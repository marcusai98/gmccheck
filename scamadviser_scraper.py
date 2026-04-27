"""
GMC Compliance Agent — ScamAdviser Scraper (v2 met ScraperAPI)
==============================================================
Werkt op VPS via ScraperAPI residentieel proxy.
ScraperAPI JS rendering aan voor ScamAdviser (laadt score async).

Setup:
    pip install httpx beautifulsoup4 playwright
    playwright install chromium
    export SCRAPERAPI_KEY="jouw_key_hier"

Usage:
    import asyncio, os
    from scamadviser_scraper import run_scamadviser_check

    results = asyncio.run(run_scamadviser_check(
        "https://maisoncozza.com",
        scraperapi_key=os.getenv("SCRAPERAPI_KEY")
    ))
"""

import asyncio
import os
import re
from urllib.parse import urlparse, urlencode

import httpx
from bs4 import BeautifulSoup

SCORE_FAIL    = 50
SCORE_WARNING = 70
SCAMADVISER_URL = "https://www.scamadviser.com/check-website/{domain}"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.scamadviser.com/",
}


def get_domain(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    return urlparse(url).netloc.lower().lstrip("www.")


def scraperapi_url(target: str, key: str) -> str:
    """ScraperAPI met JS rendering aan — nodig voor ScamAdviser's async score loading."""
    return f"https://api.scraperapi.com/?{urlencode({'api_key': key, 'url': target, 'render': 'true', 'residential': 'true', 'country_code': 'us', 'wait_for_selector': '[class*=score],[data-score]'})}"


def parse_score(html: str) -> int | None:
    soup = BeautifulSoup(html, "html.parser")
    full_text = soup.get_text()

    # Methode 1: JSON in script tags (meest betrouwbaar)
    for script in soup.find_all("script"):
        text = script.string or ""
        for p in [
            r'"trustScore"\s*:\s*(\d+)',
            r'"trust_score"\s*:\s*(\d+)',
            r'"score"\s*:\s*(\d+)',
            r'trustScore["\s]*[:=]["\s]*(\d+)',
            r'"rating"\s*:\s*(\d+)',
        ]:
            m = re.search(p, text)
            if m:
                s = int(m.group(1))
                if 1 <= s <= 100: return s

    # Methode 2: data-score / data-trust attribuut
    for attr in ["data-score", "data-trust", "data-rating"]:
        for tag in soup.find_all(attrs={attr: True}):
            try:
                s = int(tag[attr])
                if 1 <= s <= 100: return s
            except (ValueError, TypeError): continue

    # Methode 3: <span> of <div> met grote standalone nummers naast "trust" context
    for tag in soup.find_all(class_=re.compile(r"score|trust|rating|gauge|meter", re.I)):
        txt = tag.get_text(strip=True)
        m = re.match(r'^(\d{1,3})$', txt)
        if m:
            s = int(m.group(1))
            if 1 <= s <= 100: return s

    # Methode 4: "Score: 78" of "78/100" patronen in paginatekst
    for pattern in [r'[Ss]core[:\s]+(\d{1,3})', r'\b(\d{1,3})\s*/\s*100']:
        m = re.search(pattern, full_text)
        if m:
            s = int(m.group(1))
            if 1 <= s <= 100: return s

    return None


def parse_risk_factors(html: str) -> list:
    text = BeautifulSoup(html, "html.parser").get_text().lower()
    keywords = ["high risk", "young domain", "new website", "low traffic", "anonymous",
                "short life", "no reviews", "negative reviews", "phishing", "malware", "blacklisted"]
    return [k for k in keywords if k in text][:6]


async def _fetch_direct(url: str) -> tuple[int, str | None]:
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as c:
        try:
            r = await c.get(url, timeout=15)
            return r.status_code, r.text if r.status_code == 200 else None
        except httpx.RequestError:
            return 0, None


async def _fetch_scraperapi(url: str, key: str) -> tuple[int, str | None]:
    """
    ScraperAPI met render=true voor ScamAdviser.
    JS rendering kost 5 credits ipv 1 maar is noodzakelijk.
    """
    async with httpx.AsyncClient(follow_redirects=True) as c:
        try:
            r = await c.get(scraperapi_url(url, key), timeout=45)  # residential proxy
            return r.status_code, r.text if r.status_code == 200 else None
        except httpx.RequestError:
            return 0, None


async def _fetch_playwright(url: str) -> tuple[int, str | None]:
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            b = await p.chromium.launch(headless=True)
            ctx = await b.new_context(user_agent=HEADERS["User-Agent"],
                viewport={"width": 1280, "height": 800}, locale="en-US")
            page = await ctx.new_page()
            await page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf}",
                lambda route: route.abort())
            await page.goto(url, wait_until="networkidle", timeout=45000)
            try:
                await page.wait_for_selector(
                    "[class*='score'],[data-score],[class*='trust'],[class*='Trust'],[class*='Score']",
                    timeout=10000
                )
            except Exception:
                pass
            await page.wait_for_timeout(3000)
            html = await page.content()
            await b.close()
            return 200, html
    except Exception:
        return 0, None


async def run_scamadviser_check(store_url: str, scraperapi_key: str | None = None) -> dict:
    """
    Scrape ScamAdviser trust score.
    Werkt op VPS via ScraperAPI (render=true voor JS-loaded score).

    Args:
        store_url: bijv. "https://maisoncozza.com"
        scraperapi_key: ScraperAPI key (of via SCRAPERAPI_KEY env var)
    """
    api_key = scraperapi_key or os.getenv("SCRAPERAPI_KEY")
    domain = get_domain(store_url)
    check_url = SCAMADVISER_URL.format(domain=domain)

    # ScamAdviser laadt score via JS — ScraperAPI residential eerst (VPS datacenter-IP
    # wordt door Cloudflare geblokkeerd), Playwright als fallback, direct als laatste.
    html, method = None, "failed"

    # 1. ScraperAPI met JS rendering + residential proxy (meest betrouwbaar op VPS)
    if api_key:
        status, html = await _fetch_scraperapi(check_url, api_key)
        if html: method = "scraperapi+render"

    # 2. Playwright (werkt soms als Cloudflare datacenter-IP toevallig doorlaat)
    if not html:
        status, html = await _fetch_playwright(check_url)
        if html: method = "playwright"

    # 3. Direct als laatste fallback (score ontbreekt vrijwel altijd)
    if not html:
        status, html = await _fetch_direct(check_url)
        if html: method = "direct_no_js"

    if not html:
        hint = "" if api_key else "  Set SCRAPERAPI_KEY for VPS use."
        return {"domain": domain, "scamadviser_url": check_url, "status": "ERROR",
                "explanation": f"Could not reach ScamAdviser.{hint}",
                "score": None, "risk_factors": [], "fetch_method": method}

    score = parse_score(html)
    risk_factors = parse_risk_factors(html)

    if score is None:
        return {"domain": domain, "scamadviser_url": check_url, "status": "WARNING",
                "explanation": "ScamAdviser page loaded but score not found. Manual check recommended.",
                "score": None, "risk_factors": risk_factors, "fetch_method": method}

    if score < SCORE_FAIL:
        status_label = "FAIL"
        explanation = f"ScamAdviser score {score}/100 — high risk. GMC may reject this store."
    elif score < SCORE_WARNING:
        status_label = "WARNING"
        explanation = f"ScamAdviser score {score}/100 — moderate risk. GMC reviewers may flag this."
    else:
        status_label = "PASS"
        explanation = f"ScamAdviser score {score}/100 — no major concerns."

    if risk_factors:
        explanation += f" Risk factors: {', '.join(risk_factors)}."

    return {"domain": domain, "scamadviser_url": check_url, "status": status_label,
            "explanation": explanation, "score": score, "score_out_of": 100,
            "risk_factors": risk_factors, "fetch_method": method}


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://maisoncozza.com"
    key = sys.argv[2] if len(sys.argv) > 2 else os.getenv("SCRAPERAPI_KEY")
    print(f"\nScamAdviser: {url}  |  Key: {'ja' if key else 'NIET INGESTELD'}\n{'─'*46}")
    r = asyncio.run(run_scamadviser_check(url, scraperapi_key=key))
    print(f"Status: {r['status']}  |  Score: {r['score']}/100  |  Method: {r.get('fetch_method')}")
    print(f"Explanation: {r['explanation']}")

