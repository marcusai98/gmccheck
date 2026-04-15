"""
GMC Compliance Agent — Policy Scraper (v2)
==========================================
Checks shipping en refund policies met onderscheid tussen:
  - Kritieke velden (FAIL als ze missen)
  - Aanbevolen velden (WARNING als ze missen)

Kritieke velden (GMC vereist):
  Shipping: levertijd, verzendkosten
  Refund: retourvenster, retourverzending

Aanbevolen velden (WARNING):
  Shipping: landen, order cutoff
  Refund: verwerkingstijd, omruilbeleid, restocking fee

Usage:
    import asyncio
    from policy_scraper import run_policy_checks

    results = asyncio.run(run_policy_checks("https://maisoncozza.com"))
"""

import asyncio
import os
import re
from urllib.parse import urlparse, urlencode

import httpx
from bs4 import BeautifulSoup

HUMAN_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

SHIPPING_PATHS = [
    "/policies/shipping-policy", "/pages/shipping",
    "/pages/shipping-policy", "/pages/delivery",
]
REFUND_PATHS = [
    "/policies/refund-policy", "/pages/returns",
    "/pages/refund-policy", "/pages/return-policy",
]
CONTACT_PATHS = [
    "/pages/contact", "/pages/contact-us", "/pages/get-in-touch",
]

# ── Shipping velden ──────────────────────────────────────────────────────

SHIPPING_CRITICAL = {
    "delivery_time": [
        r"\d+[-–]\d+\s+(business\s+)?days?",
        r"\d+\s+(business\s+)?days?",
        r"(standard|express|expedited)\s+(shipping|delivery)",
        r"(delivery|shipping)\s+(time|timeframe|estimate|window)",
        r"arrives?\s+(in|within)\s+\d+",
        r"(within|in)\s+\d+[-–\s]\d+\s+(business\s+)?days?",
    ],
    "shipping_cost": [
        r"free\s+shipping", r"free\s+deliver",
        r"shipping\s+(cost|fee|price|rate|is\s+free)",
        r"\$[\d.]+\s*(shipping|delivery)", r"flat\s+rate",
        r"calculated\s+at\s+checkout", r"free\s+over\s+\$",
        r"no\s+shipping\s+(cost|fee|charge)",
    ],
}

SHIPPING_RECOMMENDED = {
    "shipping_countries": [
        r"(ship|deliver|shipping|delivery)\s+(to|worldwide|internationally|globally)",
        r"(united\s+states|usa|u\.s\.a?|canada|uk|europe|australia|worldwide)",
        r"(domestic|international)\s+(shipping|delivery|orders?)",
        r"countries?\s+we\s+ship", r"available\s+in",
        r"we\s+(ship|deliver)\s+to",
    ],
    "order_cutoff": [
        r"order(s)?\s+(placed|received|submitted)\s+by",
        r"cut[\s-]?off\s+time",
        r"same[\s-]day\s+(shipping|dispatch|processing)",
        r"processing\s+(time|takes?|within)",
        r"orders?\s+placed\s+before",
    ],
}

# ── Refund velden ────────────────────────────────────────────────────────

REFUND_CRITICAL = {
    "return_window": [
        r"\d+[\s-]day\s+return",
        r"return(s)?\s+within\s+\d+",
        r"within\s+\d+\s+days?\s+of\s+(purchase|delivery|receipt)",
        r"\d+\s+days?\s+to\s+return",
        r"(30|60|90|14|7)\s+day(s)?\s+(return|refund|money)",
        r"hassle[\s-]free\s+return",
    ],
    "return_shipping_cost": [
        r"(customer|buyer|you)\s+(pay|is\s+responsible|covers?)\s+(for\s+)?return",
        r"free\s+return(s)?",
        r"return\s+shipping\s+(is\s+)?(free|covered|paid|at\s+your\s+cost)",
        r"prepaid\s+return(s)?\s+label",
        r"return\s+(postage|label|cost|fee)",
        r"we\s+(cover|pay\s+for)\s+return",
    ],
}

REFUND_RECOMMENDED = {
    "refund_processing_time": [
        r"\d+[-–]\d+\s+(business\s+)?days?\s+(to\s+)?(process|refund|credit)",
        r"refund(s)?\s+(processed?|issued|applied)\s+(within|in)\s+\d+",
        r"allow\s+\d+\s+days?",
        r"processed?\s+within\s+\d+",
        r"(3|5|7|10|14)\s+(business\s+)?days?\s+(for\s+)?(refund|processing)",
    ],
    "exchange_policy": [
        r"exchange(s)?", r"swap(ped)?", r"replac(e|ement)(s)?",
        r"we\s+(do\s+not\s+accept|offer|accept)\s+exchange",
        r"no\s+exchange",
    ],
    "restocking_fee": [
        r"restocking\s+fee", r"no\s+restocking",
        r"\d+%\s+restocking", r"restock(ing)?\s+charge",
        r"no\s+(additional\s+)?fee",
    ],
}

# ── Service uren ─────────────────────────────────────────────────────────

HOURS_PATTERNS = [
    r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday)",
    r"\d{1,2}(:\d{2})?\s*(am|pm)",
    r"(business\s+hours?|office\s+hours?|support\s+hours?)",
    r"(open|available)\s+(from|between)\s+\d+",
    r"(9|10|8)\s*(am|:00)\s*(to|-|–)\s*(5|6|7|8)\s*(pm|:00)",
    r"(mon|tue|wed|thu|fri|sat|sun)[\s\-–]+(mon|tue|wed|thu|fri|sat|sun)",
    r"\d{1,2}:\d{2}\s*(am|pm)?\s*[-–]\s*\d{1,2}:\d{2}\s*(am|pm)?",
]

FIELD_LABELS = {
    "delivery_time": "Levertijd",
    "shipping_cost": "Verzendkosten",
    "shipping_countries": "Bestemmingslanden",
    "order_cutoff": "Besteltijdslimiet",
    "return_window": "Retourvenster",
    "return_shipping_cost": "Retourverzendkosten",
    "refund_processing_time": "Terugbetalingstermijn",
    "exchange_policy": "Omruilbeleid",
    "restocking_fee": "Restocking fee",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_base_url(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def scraperapi_url(target: str, key: str) -> str:
    return f"https://api.scraperapi.com/?{urlencode({'api_key': key, 'url': target, 'residential': 'true'})}"


async def fetch_page(client: httpx.AsyncClient, url: str, api_key: str | None = None) -> str | None:
    try:
        resp = await client.get(url, timeout=12, follow_redirects=True)
        if resp.status_code == 200:
            return resp.text
        # Geblokkeerd — probeer ScraperAPI
        if resp.status_code in {403, 429} and api_key:
            r2 = await client.get(scraperapi_url(url, api_key), timeout=60, follow_redirects=True)
            if r2.status_code == 200:
                return r2.text
        # Playwright fallback
        if resp.status_code in {403, 429}:
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


async def fetch_first_available(client, base_url, paths, api_key=None):
    for path in paths:
        url = base_url + path
        html = await fetch_page(client, url, api_key)
        if html:
            text = BeautifulSoup(html, "html.parser").get_text()
            if len(text.strip()) > 200:
                return html, url
    return None, None


def check_fields(text: str, patterns_dict: dict) -> dict[str, bool]:
    text_lower = text.lower()
    return {
        field: any(re.search(p, text_lower) for p in patterns)
        for field, patterns in patterns_dict.items()
    }


def content_similarity(t1: str, t2: str) -> float:
    w1, w2 = set(t1.lower().split()), set(t2.lower().split())
    if not w1 or not w2: return 0.0
    return len(w1 & w2) / len(w1 | w2)


# ---------------------------------------------------------------------------
# Individuele checks

# ---------------------------------------------------------------------------

async def check_shipping_policy(client, base_url, api_key=None) -> dict:
    html, url = await fetch_first_available(client, base_url, SHIPPING_PATHS, api_key)

    if not html:
        return {
            "status": "FAIL", "url": None,
            "explanation": "Shipping policy pagina niet gevonden op verwachte URLs.",
            "critical_missing": list(SHIPPING_CRITICAL.keys()),
            "recommended_missing": list(SHIPPING_RECOMMENDED.keys()),
        }

    text = BeautifulSoup(html, "html.parser").get_text()
    critical_found = check_fields(text, SHIPPING_CRITICAL)
    recommended_found = check_fields(text, SHIPPING_RECOMMENDED)

    critical_missing = [f for f, v in critical_found.items() if not v]
    recommended_missing = [f for f, v in recommended_found.items() if not v]

    if critical_missing:
        status = "FAIL"
        missing_labels = ", ".join(FIELD_LABELS[f] for f in critical_missing)
        explanation = f"Kritieke velden ontbreken: {missing_labels}."
    elif recommended_missing:
        status = "WARNING"
        missing_labels = ", ".join(FIELD_LABELS[f] for f in recommended_missing)
        explanation = f"Aanbevolen velden ontbreken: {missing_labels}."
    else:
        status = "PASS"
        explanation = "Shipping policy bevat alle vereiste en aanbevolen GMC-velden."

    return {
        "status": status, "url": url, "explanation": explanation,
        "critical_found": [f for f, v in critical_found.items() if v],
        "critical_missing": [FIELD_LABELS[f] for f in critical_missing],
        "recommended_found": [f for f, v in recommended_found.items() if v],
        "recommended_missing": [FIELD_LABELS[f] for f in recommended_missing],
    }


async def check_duplicate_shipping_policy(client, base_url, api_key=None) -> dict:
    pages = {}
    for path in SHIPPING_PATHS:
        url = base_url + path
        html = await fetch_page(client, url, api_key)
        if html:
            text = BeautifulSoup(html, "html.parser").get_text().strip()
            if len(text) > 300:
                pages[url] = text

    if len(pages) < 2:
        return {"status": "PASS", "explanation": "Één shipping policy pagina gevonden.", "duplicates": []}

    urls = list(pages.keys())
    duplicates = []
    for i in range(len(urls)):
        for j in range(i + 1, len(urls)):
            sim = content_similarity(pages[urls[i]], pages[urls[j]])
            if sim > 0.75:
                duplicates.append({"url_1": urls[i], "url_2": urls[j], "similarity": round(sim * 100)})

    if duplicates:
        return {"status": "FAIL",
                "explanation": f"{len(duplicates)} duplicaat shipping policy pagina(s) gevonden. GMC verwacht één definitieve pagina.",
                "duplicates": duplicates}

    return {"status": "PASS", "explanation": "Meerdere shipping pagina's met unieke content gevonden.", "duplicates": []}


async def check_refund_policy(client, base_url, api_key=None) -> dict:
    html, url = await fetch_first_available(client, base_url, REFUND_PATHS, api_key)

    if not html:
        return {
            "status": "FAIL", "url": None,
            "explanation": "Refund/retourbeleid pagina niet gevonden.",
            "critical_missing": list(REFUND_CRITICAL.keys()),
            "recommended_missing": list(REFUND_RECOMMENDED.keys()),
        }

    text = BeautifulSoup(html, "html.parser").get_text()
    critical_found = check_fields(text, REFUND_CRITICAL)
    recommended_found = check_fields(text, REFUND_RECOMMENDED)

    critical_missing = [f for f, v in critical_found.items() if not v]
    recommended_missing = [f for f, v in recommended_found.items() if not v]

    if critical_missing:
        status = "FAIL"
        missing_labels = ", ".join(FIELD_LABELS[f] for f in critical_missing)
        explanation = f"Kritieke velden ontbreken: {missing_labels}."
    elif recommended_missing:
        status = "WARNING"
        missing_labels = ", ".join(FIELD_LABELS[f] for f in recommended_missing)
        explanation = f"Aanbevolen velden ontbreken: {missing_labels}."
    else:
        status = "PASS"
        explanation = "Retourbeleid bevat alle vereiste en aanbevolen GMC-velden."

    return {
        "status": status, "url": url, "explanation": explanation,
        "critical_found": [f for f, v in critical_found.items() if v],
        "critical_missing": [FIELD_LABELS[f] for f in critical_missing],
        "recommended_found": [f for f, v in recommended_found.items() if v],
        "recommended_missing": [FIELD_LABELS[f] for f in recommended_missing],
    }


async def check_customer_service_hours(client, base_url, api_key=None) -> dict:
    html, url = await fetch_first_available(client, base_url, CONTACT_PATHS, api_key)

    if not html:
        return {"status": "WARNING", "url": None,
                "explanation": "Contactpagina niet gevonden. Klantenservice uren niet verifieerbaar."}

    text = BeautifulSoup(html, "html.parser").get_text()
    hours_found = any(re.search(p, text, re.IGNORECASE) for p in HOURS_PATTERNS)

    if hours_found:
        return {"status": "PASS", "url": url,
                "explanation": "Klantenservice uren gevonden op contactpagina."}
    return {"status": "WARNING", "url": url,
            "explanation": "Contactpagina gevonden maar geen service uren gedetecteerd. Voeg toe wanneer klanten contact kunnen opnemen."}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_policy_checks(store_url: str, scraperapi_key: str | None = None) -> dict:
    """
    Voert alle policy checks uit.

    Args:
        store_url: bijv. "https://maisoncozza.com"
        scraperapi_key: optioneel voor VPS gebruik
    """
    if not store_url.startswith("http"):
        store_url = "https://" + store_url
    base_url = get_base_url(store_url)
    api_key = scraperapi_key or os.getenv("SCRAPERAPI_KEY")

    async with httpx.AsyncClient(headers={"User-Agent": HUMAN_UA}, follow_redirects=True) as client:
        shipping, duplicate, refund, hours = await asyncio.gather(
            check_shipping_policy(client, base_url, api_key),
            check_duplicate_shipping_policy(client, base_url, api_key),
            check_refund_policy(client, base_url, api_key),
            check_customer_service_hours(client, base_url, api_key),
        )

    statuses = [shipping["status"], duplicate["status"], refund["status"], hours["status"]]
    overall = "FAIL" if "FAIL" in statuses else "WARNING" if "WARNING" in statuses else "PASS"

    return {
        "store_url": store_url,
        "overall_policy_status": overall,
        "checks": {
            "shipping_policy": shipping,
            "duplicate_shipping": duplicate,
            "refund_policy": refund,
            "customer_service_hours": hours,
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys, json
    url = sys.argv[1] if len(sys.argv) > 1 else "https://maisoncozza.com"
    key = os.getenv("SCRAPERAPI_KEY")
    print(f"\nPolicy checks: {url}\n{'─' * 50}")
    results = asyncio.run(run_policy_checks(url, scraperapi_key=key))
    for name, check in results["checks"].items():
        print(f"{name:<30} [{check['status']}]")
        if check.get("critical_missing"):
            print(f"  KRITIEK ontbreekt: {', '.join(check['critical_missing'])}")
        if check.get("recommended_missing"):
            print(f"  Aanbevolen ontbreekt: {', '.join(check['recommended_missing'])}")
        print(f"  {check.get('explanation', '')[:100]}")
    print(f"\nOverall: {results['overall_policy_status']}")

