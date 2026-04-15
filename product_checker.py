"""
GMC Compliance Agent — Product & Collection Checker (v2)
=========================================================
Regels:
  - Lege collectie (0 producten) → FAIL
  - Minder dan 5 producten → WARNING (te dun)
  - 5 of meer producten → PASS (geen maximum)

Usage:
    import asyncio
    from product_checker import run_product_checks

    results = asyncio.run(run_product_checks("https://maisoncozza.com"))
"""

import asyncio
import os
import re
from urllib.parse import urlparse, urljoin, urlencode

import httpx
from bs4 import BeautifulSoup

HUMAN_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

MIN_PRODUCTS = 5   # Minder dan dit → WARNING
# Geen MAX_PRODUCTS meer — geen bovengrens


def get_base_url(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def scraperapi_url(target: str, key: str) -> str:
    return f"https://api.scraperapi.com/?{urlencode({'api_key': key, 'url': target, 'residential': 'true'})}"


async def fetch(client: httpx.AsyncClient, url: str, api_key: str | None = None) -> str | None:
    try:
        resp = await client.get(url, timeout=12, follow_redirects=True)
        if resp.status_code == 200:
            return resp.text
        if resp.status_code in {403, 429}:
            if api_key:
                r2 = await client.get(scraperapi_url(url, api_key), timeout=60, follow_redirects=True)
                if r2.status_code == 200: return r2.text
            return await _playwright_fetch(url)
        return None
    except httpx.RequestError:
        if api_key:
            try:
                r2 = await client.get(scraperapi_url(url, api_key), timeout=60, follow_redirects=True)
                if r2.status_code == 200: return r2.text
            except Exception: pass
        return await _playwright_fetch(url)


async def _playwright_fetch(url: str) -> str | None:
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            b = await p.chromium.launch(headless=True)
            ctx = await b.new_context(user_agent=HUMAN_UA, viewport={"width": 1280, "height": 800})
            page = await ctx.new_page()
            await page.goto(url, wait_until="networkidle", timeout=25000)
            html = await page.content()
            await b.close()
            return html
    except Exception:
        return None


async def fetch_json(client: httpx.AsyncClient, url: str, api_key: str | None = None) -> dict | None:
    html = await fetch(client, url, api_key)
    if not html:
        return None
    try:
        # Als JSON endpoint, parse direct
        import json
        # Strip HTML tags als het wrapped is
        if html.strip().startswith("{") or html.strip().startswith("["):
            return json.loads(html)
        # Anders: zoek JSON in HTML response (sommige stores wrappen het)
        soup = BeautifulSoup(html, "html.parser")
        pre = soup.find("pre")
        if pre:
            return json.loads(pre.get_text())
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Collection discovery
# ---------------------------------------------------------------------------

async def get_collections_via_json(client, base_url, api_key=None) -> list[dict]:
    data = await fetch_json(client, f"{base_url}/collections.json?limit=250", api_key)
    if not data or "collections" not in data:
        return []
    return [
        {"handle": c.get("handle", ""), "title": c.get("title", ""),
         "url": f"{base_url}/collections/{c.get('handle', '')}", "id": c.get("id")}
        for c in data["collections"]
    ]


async def get_collections_via_scrape(client, base_url, api_key=None) -> list[dict]:
    html = await fetch(client, f"{base_url}/collections", api_key)
    if not html:
        return []

    soup = BeautifulSoup(html, "html.parser")
    collections, seen = [], set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/collections/" not in href or href in seen:
            continue
        # Sla "all" collectie over
        if href.rstrip("/").endswith("/collections/all"):
            continue
        full_url = urljoin(base_url, href)
        handle = href.rstrip("/").split("/")[-1]
        title = a.get_text(strip=True) or handle
        if title and len(title) < 60:  # Filter navigatie-ruis
            collections.append({"handle": handle, "title": title, "url": full_url})
            seen.add(href)

    return collections


async def get_product_count_via_json(client, base_url, handle, api_key=None) -> int | None:
    data = await fetch_json(client, f"{base_url}/collections/{handle}/products.json?limit=250", api_key)
    if data and "products" in data:
        return len(data["products"])
    return None


async def get_product_count_via_scrape(client, collection_url, api_key=None) -> int | None:
    html = await fetch(client, collection_url, api_key)
    if not html:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Zoek "X products" tekst — meest betrouwbaar
    text = soup.get_text()
    m = re.search(r"(\d+)\s+products?", text, re.IGNORECASE)
    if m:
        return int(m.group(1))

    # Shopify product card selectors
    for selector in ["[class*='product-item']", "[class*='product-card']",
                     "[class*='grid-product']", "[data-product-id]", "li[class*='product']"]:
        items = soup.select(selector)
        if items: return len(items)

    # Tel unieke product links
    unique = set()
    for a in soup.find_all("a", href=re.compile(r"/products/")):
        m2 = re.search(r"/products/([^/?#]+)", a.get("href", ""))
        if m2: unique.add(m2.group(1))
    if unique: return len(unique)

    return None


# ---------------------------------------------------------------------------
# Collection evaluatie
# ---------------------------------------------------------------------------

async def check_collection(client, base_url, collection, api_key=None) -> dict:
    count = await get_product_count_via_json(client, base_url, collection["handle"], api_key)
    method = "json"

    if count is None:
        count = await get_product_count_via_scrape(client, collection["url"], api_key)
        method = "scrape"

    if count is None:
        return {**collection, "product_count": None, "status": "WARNING",
                "explanation": "Productaantal niet te bepalen.", "method": method}

    if count == 0:
        status = "FAIL"
        explanation = "Lege collectie — 0 producten. GMC kan lege collecties penaliseren."
    elif count < MIN_PRODUCTS:
        status = "WARNING"
        explanation = (f"{count} product(en). Minimaal {MIN_PRODUCTS} aanbevolen voor een "
                       "gevulde collectie die GMC reviewers overtuigt.")
    else:
        status = "PASS"
        explanation = f"{count} producten — voldoet aan de minimumvereiste van {MIN_PRODUCTS}."

    return {**collection, "product_count": count, "status": status,
            "explanation": explanation, "method": method}


async def check_total_products(client, base_url, api_key=None) -> dict:
    data = await fetch_json(client, f"{base_url}/products.json?limit=250", api_key)
    if not data:
        return {"total_products": None, "status": "WARNING",
                "explanation": "Totaal productaantal niet opgehaald."}
    count = len(data.get("products", []))
    return {"total_products": count,
            "status": "PASS" if count > 0 else "FAIL",
            "explanation": f"Store heeft {count} product(en) in totaal."}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_product_checks(store_url: str, scraperapi_key: str | None = None) -> dict:
    """
    Voert alle product en collectie compliance checks uit.

    Args:
        store_url: bijv. "https://maisoncozza.com"
        scraperapi_key: optioneel voor VPS gebruik
    """
    if not store_url.startswith("http"):
        store_url = "https://" + store_url
    base_url = get_base_url(store_url)
    api_key = scraperapi_key or os.getenv("SCRAPERAPI_KEY")

    async with httpx.AsyncClient(headers={"User-Agent": HUMAN_UA}, follow_redirects=True) as client:

        # Collecties ophalen
        collections = await get_collections_via_json(client, base_url, api_key)
        method = "json"
        if not collections:
            collections = await get_collections_via_scrape(client, base_url, api_key)
            method = "scrape"

        if not collections:
            return {
                "store_url": store_url, "overall_product_status": "WARNING",
                "discovery_method": "failed", "collections_found": 0,
                "checks": {
                    "collections": [],
                    "empty_collections": {"status": "WARNING",
                        "explanation": "Geen collecties gevonden of store niet toegankelijk.", "count": 0},
                    "thin_collections": {"count": 0, "items": []},
                    "total_products": {"total_products": None, "status": "WARNING",
                        "explanation": "Geen productdata opgehaald."},
                },
            }

        # Controleer elke collectie parallel
        col_results, total = await asyncio.gather(
            asyncio.gather(*[check_collection(client, base_url, c, api_key) for c in collections]),
            check_total_products(client, base_url, api_key),
        )

        empty = [c for c in col_results if c.get("product_count") == 0]
        thin  = [c for c in col_results if c.get("product_count") and 0 < c["product_count"] < MIN_PRODUCTS]

        empty_status = "FAIL" if empty else "PASS"
        empty_explanation = (
            f"{len(empty)} lege collectie(s): " + ", ".join(c["title"] for c in empty)
            if empty else "Geen lege collecties."
        )

        all_statuses = [c["status"] for c in col_results]
        overall = "FAIL" if "FAIL" in all_statuses else "WARNING" if "WARNING" in all_statuses else "PASS"

    return {
        "store_url": store_url,
        "overall_product_status": overall,
        "discovery_method": method,
        "collections_found": len(collections),
        "checks": {
            "collections": list(col_results),
            "empty_collections": {
                "status": empty_status, "explanation": empty_explanation,
                "count": len(empty),
                "empty_items": [{"title": c["title"], "url": c["url"]} for c in empty],
            },
            "thin_collections": {
                "count": len(thin),
                "items": [{"title": c["title"], "product_count": c["product_count"],
                           "url": c["url"]} for c in thin],
            },
            "total_products": total,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys, json
    url = sys.argv[1] if len(sys.argv) > 1 else "https://maisoncozza.com"
    key = os.getenv("SCRAPERAPI_KEY")
    print(f"\nProduct checks: {url}\n{'─' * 50}")
    results = asyncio.run(run_product_checks(url, scraperapi_key=key))
    print(f"Collecties: {results['collections_found']} ({results['discovery_method']})")
    print(f"Overall:    {results['overall_product_status']}")
    print(f"Totaal:     {results['checks']['total_products'].get('total_products')} producten")
    print(f"Leeg:       {results['checks']['empty_collections']['count']}")
    print(f"Te dun (<{MIN_PRODUCTS}): {results['checks']['thin_collections']['count']}")
    print("\nPer collectie:")
    for c in results["checks"]["collections"]:
        print(f"  [{c['status']}] {c['title']:<35} {c.get('product_count', '?')} producten")

