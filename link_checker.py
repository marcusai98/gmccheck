"""
GMC Compliance Agent — Link Checker Module
==========================================
Drop this file into your OpenClaw agent's tool registry.

Performs three checks in a single crawl:
  1. Broken links       — 404s and non-2xx on critical pages
  2. Wrong-domain links — links pointing to a different store domain
  3. Email mismatches   — contact emails not matching the store domain

Strategy:
  - Fast path: httpx (async, no browser) for most stores
  - Fallback:  Playwright headless Chromium if store blocks bots (403/429)

Usage:
    import asyncio
    from link_checker import run_link_check

    results = asyncio.run(run_link_check("https://realsabai.com"))

Returns a dict ready to merge into the agent's scan context object.
"""

import asyncio
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PRIORITY_PATHS = [
    "/pages/contact",
    "/pages/contact-us",
    "/pages/get-in-touch",
    "/policies/refund-policy",
    "/policies/shipping-policy",
    "/policies/privacy-policy",
    "/policies/terms-of-service",
    "/pages/about-us",
    "/pages/frequently-asked-questions",
    "/pages/frequently-asked-question",
    "/pages/faq",
    "/pages/do-not-sell-my-data",
    "/policies/contact-information",
]

ALLOWED_EXTERNAL_PATTERNS = [
    "paypal.com", "shopify.com", "apps.shopify", "cdn.shopify",
    "myshopify.com", "fonts.googleapis", "googletagmanager",
    "google-analytics", "facebook.com", "instagram.com", "tiktok.com",
    "twitter.com", "x.com", "youtube.com", "maps.google",
    "maps.app.goo.gl", "goo.gl", "g.page", "linktr.ee",
    "pinterest.com", "trustpilot.com", "reviews.io", "judge.me",
    "klaviyo.com", "mailchimp.com", "afterpay.com", "klarna.com",
    "paypal.com", "stripe.com", "shopify.com", "cdn.shopify",
    "afterpay.com", "klarna.com", "affirm.com", "trustpilot.com",
]

BROKEN_STATUSES = {400, 404, 405, 410, 500, 502, 503}
TRANSIENT_STATUSES = {500, 502, 503}  # retry these once — often temporary
BOT_BLOCK_STATUSES = {403, 429}

REQUEST_TIMEOUT = 12
CONCURRENCY = 20

HUMAN_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class BrokenLink:
    url: str
    status_code: int
    found_on: str
    link_text: str = ""
    def to_dict(self):
        return {"url": self.url, "status_code": self.status_code,
                "found_on": self.found_on, "link_text": self.link_text}


@dataclass
class WrongDomainLink:
    url: str
    wrong_domain: str
    found_on: str
    link_text: str = ""
    page_type: str = ""
    def to_dict(self):
        return {"url": self.url, "wrong_domain": self.wrong_domain,
                "found_on": self.found_on, "link_text": self.link_text,
                "page_type": self.page_type}


@dataclass
class EmailMismatch:
    email: str
    email_domain: str
    found_on: str
    def to_dict(self):
        return {"email": self.email, "email_domain": self.email_domain,
                "found_on": self.found_on}


@dataclass
class LinkCheckResult:
    store_url: str
    store_domain: str
    fetch_method: str = "httpx"
    pages_crawled: list = field(default_factory=list)
    broken_links: list = field(default_factory=list)
    wrong_domain_links: list = field(default_factory=list)
    email_mismatches: list = field(default_factory=list)
    errors: list = field(default_factory=list)

    @property
    def broken_links_status(self):
        # 404/410 = truly gone → FAIL; 5xx = server errors (transient) → WARNING only
        hard_broken = [b for b in self.broken_links if b.status_code in {404, 410}]
        if hard_broken: return "FAIL"
        if self.broken_links: return "WARNING"
        return "PASS"

    @property
    def wrong_domain_status(self):
        return "FAIL" if self.wrong_domain_links else "PASS"

    @property
    def email_mismatch_status(self):
        return "FAIL" if self.email_mismatches else "PASS"

    def to_dict(self):
        return {
            "store_url": self.store_url,
            "store_domain": self.store_domain,
            "fetch_method": self.fetch_method,
            "pages_crawled": len(self.pages_crawled),
            "checks": {
                "broken_links": {
                    "status": self.broken_links_status,
                    "count": len(self.broken_links),
                    "items": [b.to_dict() for b in self.broken_links],
                },
                "wrong_domain_links": {
                    "status": self.wrong_domain_status,
                    "count": len(self.wrong_domain_links),
                    "items": [w.to_dict() for w in self.wrong_domain_links],
                },
                "email_mismatches": {
                    "status": self.email_mismatch_status,
                    "count": len(self.email_mismatches),
                    "items": [e.to_dict() for e in self.email_mismatches],
                },
            },
            "errors": self.errors,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_store_domain(url):
    netloc = urlparse(url).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc

def is_allowed_external(url):
    return any(p in url.lower() for p in ALLOWED_EXTERNAL_PATTERNS)

def classify_page_type(url):
    if "/policies/" in url: return "Policy"
    if "/pages/" in url: return "Page"
    if "/products/" in url: return "Product"
    if "/collections/" in url: return "Collection"
    return "Other"

def extract_emails(text):
    # Word boundary after TLD prevents "support@domain.comSomeText" matches
    raw = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6}(?=[^a-zA-Z0-9]|$)", text)
    return list(dict.fromkeys(raw))  # deduplicate, preserve order

def extract_links(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if not href or href.startswith(("#", "javascript:", "tel:")):
            continue
        if href.startswith("mailto:"):
            email = href.replace("mailto:", "").split("?")[0].strip()
            if email:
                links.append(("__email__:" + email, ""))
            continue
        links.append((urljoin(base_url, href), tag.get_text(strip=True)[:80]))
    return links

def dedupe(items, key_fn):
    seen = set()
    out = []
    for item in items:
        k = key_fn(item)
        if k not in seen:
            seen.add(k)
            out.append(item)
    return out


# ---------------------------------------------------------------------------
# Fetch strategies
# ---------------------------------------------------------------------------

async def fetch_httpx(client, url):
    try:
        head = await client.head(url, follow_redirects=True, timeout=REQUEST_TIMEOUT)
        if head.status_code >= 400:
            return head.status_code, None
        if "text/html" not in head.headers.get("content-type", ""):
            return head.status_code, None
        get = await client.get(url, follow_redirects=True, timeout=REQUEST_TIMEOUT)
        return get.status_code, get.text
    except httpx.TimeoutException:
        return 408, None
    except httpx.RequestError:
        return None, None


async def fetch_playwright(url):
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            ctx = await browser.new_context(
                user_agent=HUMAN_UA,
                viewport={"width": 1280, "height": 800},
            )
            page = await ctx.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)
            html = await page.content()
            await browser.close()
            return 200, html
    except Exception:
        return None, None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_link_check(store_url: str) -> dict:
    """
    Full GMC link compliance check. Single crawl, three checks.

    Args:
        store_url: Full store URL e.g. "https://realsabai.com"

    Returns:
        Structured dict ready for agent scan context.
    """
    if not store_url.startswith("http"):
        store_url = "https://" + store_url
    store_url = store_url.rstrip("/")

    store_domain = get_store_domain(store_url)
    result = LinkCheckResult(store_url=store_url, store_domain=store_domain)
    semaphore = asyncio.Semaphore(CONCURRENCY)
    pages_to_crawl = [store_url] + [store_url + p for p in PRIORITY_PATHS]

    async with httpx.AsyncClient(
        headers={"User-Agent": HUMAN_UA}, follow_redirects=True
    ) as client:

        # ── Probe homepage: detect bot blocking ───────────────────────────
        probe_status, _ = await fetch_httpx(client, store_url)
        use_playwright = probe_status in BOT_BLOCK_STATUSES or probe_status is None
        result.fetch_method = "playwright" if use_playwright else "httpx"

        # ── Fetch all priority pages ───────────────────────────────────────
        async def fetch_page(url):
            async with semaphore:
                if use_playwright:
                    return url, *await fetch_playwright(url)
                return url, *await fetch_httpx(client, url)

        responses = await asyncio.gather(*[fetch_page(u) for u in pages_to_crawl])

        # ── Parse: collect links and emails ───────────────────────────────
        all_links: dict = {}

        for page_url, status, html in responses:
            if status is not None and status not in BROKEN_STATUSES:
                result.pages_crawled.append(page_url)
            elif status in BROKEN_STATUSES:
                result.broken_links.append(BrokenLink(
                    url=page_url,
                    status_code=status,
                    found_on="Scanner: priority page check",
                ))

            if not html:
                continue

            all_links[page_url] = extract_links(html, page_url)

            # Email mismatch check
            page_text = BeautifulSoup(html, "html.parser").get_text()
            emails = set(extract_emails(page_text))
            for link_url, _ in all_links[page_url]:
                if link_url.startswith("__email__:"):
                    emails.add(link_url.replace("__email__:", ""))

            for email in emails:
                email_domain = email.split("@")[-1].lower().lstrip("www.")
                if email_domain in {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com"}:
                    continue
                if email_domain != store_domain:
                    result.email_mismatches.append(EmailMismatch(
                        email=email,
                        email_domain=email_domain,
                        found_on=page_url,
                    ))

        # ── Classify links: internal vs wrong-domain ─────────────────────
        internal: dict = {}
        link_texts: dict = {}

        for page_url, links in all_links.items():
            for link_url, link_text in links:
                if link_url.startswith("__email__:"):
                    continue
                link_domain = urlparse(link_url).netloc.lower().lstrip("www.")
                if not link_domain:
                    continue

                if link_domain == store_domain:
                    if link_url not in internal:
                        internal[link_url] = page_url
                        link_texts[link_url] = link_text

                elif not is_allowed_external(link_url):
                    # Deduplicate: only add each unique URL once
                    if not any(w.url == link_url for w in result.wrong_domain_links):
                        result.wrong_domain_links.append(WrongDomainLink(
                            url=link_url,
                            wrong_domain=link_domain,
                            found_on=page_url,
                            link_text=link_text,
                            page_type=classify_page_type(page_url),
                        ))

        # ── Check all internal links ──────────────────────────────────────
        async def check_link(url):
            async with semaphore:
                status, _ = await fetch_httpx(client, url)
                # Retry once on transient server errors (500/502/503 are often temporary)
                if status in TRANSIENT_STATUSES:
                    await asyncio.sleep(1.5)
                    status, _ = await fetch_httpx(client, url)
                return url, status

        # Only check meaningful links — skip product/blog/account/search pages
        # (product pages are always populated; we care about nav, policies, collections)
        SKIP_PATTERNS = (
            "/products/",
            "cdn.shopify.com", ".jpg", ".png", ".gif", ".webp", ".svg", ".css", ".js",
        )
        meaningful_links = [
            url for url in internal
            if not any(pat in url.lower() for pat in SKIP_PATTERNS)
        ]
        # Cap at 60 as a safety net
        internal_sample = meaningful_links[:60]
        link_checks = await asyncio.gather(
            *[check_link(url) for url in internal_sample],
            return_exceptions=True,
        )

        for item in link_checks:
            if isinstance(item, Exception):
                continue
            url, status = item
            if status in BROKEN_STATUSES:
                result.broken_links.append(BrokenLink(
                    url=url,
                    status_code=status,
                    found_on=internal[url],
                    link_text=link_texts.get(url, ""),
                ))

        # ── Deduplicate ───────────────────────────────────────────────────
        result.broken_links = dedupe(result.broken_links, lambda x: x.url)
        result.wrong_domain_links = dedupe(result.wrong_domain_links, lambda x: (x.url, x.found_on))
        result.email_mismatches = dedupe(result.email_mismatches, lambda x: (x.email, x.found_on))

    return result.to_dict()


# ---------------------------------------------------------------------------
# CLI — python link_checker.py https://yourstore.com
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys, json

    url = sys.argv[1] if len(sys.argv) > 1 else "https://realsabai.com"
    print(f"\nScanning: {url}\n{'─' * 52}")

    results = asyncio.run(run_link_check(url))

    print(f"Fetch method:        {results['fetch_method']}")
    print(f"Pages crawled:       {results['pages_crawled']}")
    print(f"Broken links:        {results['checks']['broken_links']['count']:>3}  [{results['checks']['broken_links']['status']}]")
    print(f"Wrong-domain links:  {results['checks']['wrong_domain_links']['count']:>3}  [{results['checks']['wrong_domain_links']['status']}]")
    print(f"Email mismatches:    {results['checks']['email_mismatches']['count']:>3}  [{results['checks']['email_mismatches']['status']}]")
    print("\n── Full JSON ──")
    print(json.dumps(results, indent=2))

