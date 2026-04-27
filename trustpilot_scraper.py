"""
GMC Compliance Agent — Trustpilot Scraper (v2 met ScraperAPI)
==============================================================
Werkt op VPS via ScraperAPI residentieel proxy.
Gratis tier: 5.000 credits/maand → https://www.scraperapi.com

Setup:
    pip install httpx beautifulsoup4
    export SCRAPERAPI_KEY="jouw_key_hier"

Usage:
    import asyncio, os
    from trustpilot_scraper import run_trustpilot_check

    results = asyncio.run(run_trustpilot_check(
        "https://maisoncozza.com",
        scraperapi_key=os.getenv("SCRAPERAPI_KEY")
    ))
"""

import asyncio
import json
import os
import re
from urllib.parse import urlparse, urlencode

import httpx
from bs4 import BeautifulSoup

SCORE_FAIL    = 3.0   # < 3.0 → FAIL (harde GMC grens)
SCORE_WARNING = 3.0   # no WARNING zone — direct PASS above 3.0
MIN_REVIEWS   = 5
TRUSTPILOT_BASE = "https://www.trustpilot.com/review/"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def get_domain(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    netloc = urlparse(url).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc


def scraperapi_url(target: str, key: str) -> str:
    return f"https://api.scraperapi.com/?{urlencode({'api_key': key, 'url': target, 'residential': 'true', 'country_code': 'us'})}"


def extract_json_ld(html: str) -> list:
    soup = BeautifulSoup(html, "html.parser")
    results = []
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            results.append(json.loads(tag.string or ""))
        except (json.JSONDecodeError, TypeError):
            continue
    return results


def find_aggregate_rating(blocks: list):
    for block in blocks:
        if block.get("@type") == "AggregateRating": return block
        if "aggregateRating" in block: return block["aggregateRating"]
        if isinstance(block, list):
            for item in block:
                if isinstance(item, dict) and "aggregateRating" in item:
                    return item["aggregateRating"]
    return None


def extract_review_count(soup) -> int | None:
    text = soup.get_text()
    for p in [r"([\d,]+)\s+reviews?", r"Based on\s+([\d,]+)"]:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            try: return int(m.group(1).replace(",", ""))
            except ValueError: continue
    return None


async def _fetch_direct(url: str) -> tuple[int, str | None]:
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True) as c:
        try:
            r = await c.get(url, timeout=15)
            return r.status_code, r.text if r.status_code == 200 else None
        except httpx.RequestError:
            return 0, None


async def _fetch_scraperapi(url: str, key: str) -> tuple[int, str | None]:
    async with httpx.AsyncClient(follow_redirects=True) as c:
        try:
            r = await c.get(scraperapi_url(url, key), timeout=60)
            return r.status_code, r.text if r.status_code == 200 else None
        except httpx.RequestError:
            return 0, None


async def _fetch_playwright(url: str) -> tuple[int, str | None]:
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            b = await p.chromium.launch(headless=True)
            ctx = await b.new_context(user_agent=HEADERS["User-Agent"], viewport={"width": 1280, "height": 800})
            page = await ctx.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)
            html = await page.content()
            await b.close()
            return 200, html
    except Exception:
        return 0, None


async def run_trustpilot_check(store_url: str, scraperapi_key: str | None = None) -> dict:
    api_key = scraperapi_key or os.getenv("SCRAPERAPI_KEY")
    domain = get_domain(store_url)
    tp_url = TRUSTPILOT_BASE + domain

    # Fetch prioriteit: direct → ScraperAPI → Playwright
    html, method = None, "failed"
    status, html = await _fetch_direct(tp_url)
    if html:
        method = "direct"
    elif api_key:
        status, html = await _fetch_scraperapi(tp_url, api_key)
        if html: method = "scraperapi"
    if not html:
        status, html = await _fetch_playwright(tp_url)
        if html: method = "playwright"

    if not html:
        hint = "" if api_key else "  Set SCRAPERAPI_KEY for VPS use."
        return {"domain": domain, "trustpilot_url": tp_url, "status": "ERROR",
                "explanation": f"Could not reach Trustpilot.{hint}",
                "score": None, "review_count": None, "score_label": None,
                "present": False, "fetch_method": method}

    soup = BeautifulSoup(html, "html.parser")

    # Controleer of pagina bestaat (404)
    page_text = soup.get_text().lower()
    if "page not found" in page_text or ("404" in page_text and len(page_text) < 500):
        return {"domain": domain, "trustpilot_url": tp_url, "status": "WARNING",
                "explanation": "No Trustpilot page found. Not a FAIL but increases review risk.",
                "score": None, "review_count": None, "score_label": None,
                "present": False, "fetch_method": method}

    # Parse score via JSON-LD
    rating = find_aggregate_rating(extract_json_ld(html))
    score = review_count = None
    if rating:
        try:
            score = float(rating.get("ratingValue", 0))
            review_count = int(str(rating.get("reviewCount", 0)).replace(",", ""))
        except (ValueError, TypeError):
            pass

    if score is None:
        m = re.search(r"\b([1-5](?:\.\d)?)\s*(?:out of 5|\/5)?", soup.get_text())
        if m:
            try: score = float(m.group(1))
            except ValueError: pass

    if review_count is None:
        review_count = extract_review_count(soup)

    label_map = {(4.5,5.0):"Excellent",(3.5,4.5):"Great",(2.5,3.5):"Average",(1.5,2.5):"Poor",(0.0,1.5):"Bad"}
    score_label = next((l for (lo,hi),l in label_map.items() if score and lo <= score <= hi), None)

    if score is None:
        status_label, explanation = "WARNING", "Page loaded but score not found. Manual check recommended."
    elif score < SCORE_FAIL:
        status_label = "FAIL"
        explanation = (f"Score {score:.1f}/5 ({score_label}) — below the hard threshold of 3.0. "
            "GMC requires a minimum of 3 stars on Trustpilot.")
    elif review_count is not None and review_count < MIN_REVIEWS:
        status_label = "WARNING"
        explanation = (f"Score {score:.1f}/5 but only {review_count} review(s) — "
            "te weinig reviews voor een betrouwbaar trust signaal.")
    else:
        status_label = "PASS"
        explanation = (f"Score {score:.1f}/5 ({score_label}) based on "
            f"{review_count or 'unknown'} reviews — meets the 3.0 threshold.")

    return {"domain": domain, "trustpilot_url": tp_url, "status": status_label,
            "explanation": explanation, "score": score, "review_count": review_count,
            "score_label": score_label, "present": True, "fetch_method": method}


if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://maisoncozza.com"
    key = sys.argv[2] if len(sys.argv) > 2 else os.getenv("SCRAPERAPI_KEY")
    print(f"\nTrustpilot: {url}  |  Key: {'ja' if key else 'NIET INGESTELD'}\n{'─'*46}")
    r = asyncio.run(run_trustpilot_check(url, scraperapi_key=key))
    print(f"Status: {r['status']}  |  Score: {r['score']}/5  |  Method: {r.get('fetch_method')}")
    print(f"Explanation: {r.get('explanation')}")

