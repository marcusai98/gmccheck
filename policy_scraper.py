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

SHIPPING_CRITICAL_BY_LANG = {
    "en": {
        "delivery_time": [
            r"\d+[-–]\d+\s+(business\s+)?days?",
            r"\d+\s+(business\s+)?days?",
            r"(standard|express|expedited)\s+(shipping|delivery)",
            r"(delivery|shipping)\s+(time|timeframe|estimate|window)",
            r"arrives?\s+(in|within)\s+\d+",
            r"(within|in)\s+\d+[-–\s]\d+\s+(business\s+)?days?",
        ],
        "shipping_cost": [
            r"free\s+shipping",
            r"free\s+deliver",
            r"shipping\s+(cost|fee|price|rate|is\s+free)",
            r"\$[\d.]+\s*(shipping|delivery)",
            r"flat\s+rate",
            r"calculated\s+at\s+checkout",
            r"free\s+over\s+\$",
            r"no\s+shipping\s+(cost|fee|charge)",
        ],
    },
    "de": {
        "delivery_time": [
            r"\d+[-–]\d+\s+werktag",
            r"\d+\s+werktag",
            r"lieferzeit",
            r"lieferdauer",
            r"liefert\s+in",
            r"versanddauer",
            r"zustellung\s+(innerhalb|in)\s+\d+",
            r"lieferung\s+(innerhalb|in|erfolgt)",
            r"\d+[-–]\d+\s+arbeitstag",
        ],
        "shipping_cost": [
            r"versandkost",
            r"versandfrei",
            r"kostenlos(er)?\s+versand",
            r"gratis\s+versand",
            r"versandkosten\s+(ab|frei|kostenlos|betragen)",
            r"porto",
            r"€[\d,.]+\s*versand",
            r"versandkosten\s+werden",
        ],
    },
    "nl": {
        "delivery_time": [
            r"levertijd",
            r"levert\s+binnen",
            r"verzendtijd",
            r"\d+[-–]\d+\s+werkdag",
            r"binnen\s+\d+\s+werkdag",
            r"\d+\s+werkdag",
        ],
        "shipping_cost": [
            r"verzendkost",
            r"gratis\s+verzend",
            r"verzending\s+(gratis|vrij|kosten)",
            r"portokost",
            r"verzendkosten",
        ],
    },
    "fr": {
        "delivery_time": [
            r"délai\s+de\s+livraison",
            r"livraison\s+en\s+\d+",
            r"jours?\s+ouvrables?",
            r"jours?\s+ouvré",
            r"délai\s+d.expédition",
        ],
        "shipping_cost": [
            r"frais\s+de\s+port",
            r"livraison\s+gratuite",
            r"port\s+offert",
            r"frais\s+de\s+livraison",
            r"expédition\s+gratuite",
        ],
    },
    "es": {
        "delivery_time": [
            r"tiempo\s+de\s+entrega",
            r"plazo\s+de\s+entrega",
            r"días?\s+hábiles?",
            r"días?\s+laborables?",
            r"envío\s+en\s+\d+",
        ],
        "shipping_cost": [
            r"gastos?\s+de\s+envío",
            r"envío\s+gratuito",
            r"envío\s+gratis",
            r"costes?\s+de\s+envío",
        ],
    },
}

SHIPPING_RECOMMENDED = {
    "shipping_countries": [
        # English
        r"(ship|deliver|shipping|delivery)\s+(to|worldwide|internationally|globally)",
        r"(united\s+states|usa|u\.s\.a?|canada|uk|europe|australia|worldwide)",
        r"(domestic|international)\s+(shipping|delivery|orders?)",
        r"countries?\s+we\s+ship", r"available\s+in",
        r"we\s+(ship|deliver)\s+to",
        # German
        r"wir\s+(liefern|versenden)\s+(in|nach|international)",
        r"versand\s+(in|nach|weltweit|international)",
        r"(deutschland|österreich|schweiz|europa|weltweit)\s+(versand|lieferung)",
        r"liefern\s+(wir\s+)?(in|nach)\s+\w+",
        # Dutch
        r"wij\s+(verzenden|leveren)\s+(naar|in|wereldwijd)",
        r"verzending\s+(naar|in|internationaal)",
        # French
        r"nous\s+livrons?\s+(en|à|dans|partout)",
        r"livraison\s+(internationale|en\s+france|dans\s+le\s+monde)",
    ],
    "order_cutoff": [
        # English
        r"order(s)?\s+(placed|received|submitted)\s+by",
        r"cut[\s-]?off\s+time",
        r"same[\s-]day\s+(shipping|dispatch|processing)",
        r"processing\s+(time|takes?|within)",
        r"orders?\s+placed\s+before",
        # German
        r"bestellung(en)?\s+(bis|vor)\s+\d+",
        r"bearbeitungszeit", r"bestellungen?\s+werden\s+(am|noch)\s+(selben|gleichen)\s+tag",
        r"expressversand", r"vor\s+\d+\s+uhr\s+bestell",
        # Dutch
        r"bestelling(en)?\s+(voor|vóór)\s+\d+",
        r"verwerkingstijd", r"voor\s+\d+\s+uur\s+bestell",
    ],
}

# ── Refund velden ────────────────────────────────────────────────────────

REFUND_CRITICAL_BY_LANG = {
    "en": {
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
    },
    "de": {
        "return_window": [
            r"\d+\s+(tage|tagen)\s+(rückgabe|rücksendung|widerruf|rückgaberecht)",
            r"rückgabefrist",
            r"widerrufsfrist",
            r"rückgaberecht",
            r"innerhalb\s+von\s+\d+\s+tagen",
            r"\d+[\s-]tägig(es?)?\s+(rückgabe|widerruf)",
            r"\d+\s+tage\s+rückgabe",
        ],
        "return_shipping_cost": [
            r"rücksendekosten",
            r"rückversand\s+(kostenlos|gratis|kostenfrei|auf\s+kosten)",
            r"kostenlose\s+(rücksendung|rückgabe|retoure)",
            r"rücksendung\s+(ist\s+)?(kostenlos|kostenfrei|gratis)",
            r"porto\s+(wird\s+)?(erstattet|übernommen|kostenlos)",
            r"rückgabe\s+kostenlos",
        ],
    },
    "nl": {
        "return_window": [
            r"\d+\s+dag(en)?\s+(retour|terugsturen|retourneren)",
            r"retourperiode",
            r"retourneren\s+binnen\s+\d+",
            r"\d+\s+dag(en)?\s+bedenktijd",
        ],
        "return_shipping_cost": [
            r"retourkosten",
            r"gratis\s+retour",
            r"retourverzending\s+(gratis|kosteloos)",
            r"kosten\s+voor\s+retour",
        ],
    },
    "fr": {
        "return_window": [
            r"\d+\s+jours?\s+(pour\s+)?(retourner|renvoyer|retour)",
            r"droit\s+de\s+rétractation",
            r"délai\s+de\s+retour",
            r"\d+\s+jours?\s+pour\s+changer",
        ],
        "return_shipping_cost": [
            r"frais\s+de\s+retour",
            r"retour\s+gratuit",
            r"retour\s+offert",
            r"remboursement\s+des\s+frais",
        ],
    },
    "es": {
        "return_window": [
            r"\d+\s+días?\s+(para\s+)?(devolución|devolver|retorno)",
            r"plazo\s+de\s+devolución",
            r"política\s+de\s+devolución",
        ],
        "return_shipping_cost": [
            r"gastos?\s+de\s+devolución",
            r"devolución\s+gratuita",
            r"devolución\s+gratis",
        ],
    },
}

REFUND_RECOMMENDED = {
    "refund_processing_time": [
        # English
        r"\d+[-–]\d+\s+(business\s+)?days?\s+(to\s+)?(process|refund|credit)",
        r"refund(s)?\s+(processed?|issued|applied)\s+(within|in)\s+\d+",
        r"allow\s+\d+\s+days?",
        r"processed?\s+within\s+\d+",
        r"(3|5|7|10|14)\s+(business\s+)?days?\s+(for\s+)?(refund|processing)",
        # German
        r"rückerstattung.{0,30}\d+\s+tag",
        r"\d+\s+tage?\s+(kann\s+)?(dauern|bearbeitung|verarbeitung)",
        r"bis\s+zu\s+\d+\s+tage",
        r"bearbeitungszeit.{0,20}erstattung",
        r"innerhalb.{0,20}\d+.{0,10}tag.{0,20}erstatt",
        r"erstattung.{0,30}\d+\s+werktag",
        # Dutch
        r"terugbetaling.{0,20}\d+\s+dag",
        r"restitutie.{0,20}\d+\s+dag",
        r"binnen\s+\d+\s+dag.{0,10}terugbet",
        # French
        r"remboursement.{0,20}(sous|dans|en)\s+\d+\s+jour",
        r"\d+\s+jours?.{0,20}remboursement",
    ],
    "exchange_policy": [
        # English
        r"exchange(s)?", r"swap(ped)?", r"replac(e|ement)(s)?",
        r"we\s+(do\s+not\s+accept|offer|accept)\s+exchange",
        r"no\s+exchange",
        # German
        r"umtausch", r"austausch", r"tauschen\s+möchten",
        r"artikel\s+(gegen|umtauschen)", r"gegen\s+ein\s+anderes\s+produkt",
        # Dutch
        r"omruil", r"ruilen", r"artikel\s+ruilen",
        # French
        r"échange(r)?", r"article\s+contre",
    ],
    "restocking_fee": [
        # English
        r"restocking\s+fee", r"no\s+restocking",
        r"\d+%\s+restocking", r"restock(ing)?\s+charge",
        r"no\s+(additional\s+)?fee",
        # German
        r"wiedereinlagerung", r"keine\s+wiedereinlagerungsgebühr",
        r"wiedereinlagerungsgebühr", r"keine\s+bearbeitungsgebühr",
        r"keine\s+zusätzlichen\s+(kosten|gebühren)",
        # Dutch
        r"herbevoorradingskosten", r"geen\s+extra\s+kosten",
        # French
        r"frais\s+de\s+restockage", r"aucun\s+frais\s+supplémentaire",
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


def detect_language(html: str) -> str:
    """Detect page language from HTML lang attribute or meta tags. Returns 2-letter code."""
    soup = BeautifulSoup(html, "html.parser")
    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang"):
        return html_tag["lang"].lower().split("-")[0].split("_")[0][:2]
    meta = soup.find("meta", attrs={"http-equiv": re.compile("content-language", re.I)})
    if meta and meta.get("content"):
        return meta["content"].lower().split("-")[0][:2]
    meta2 = soup.find("meta", attrs={"name": re.compile("^language$", re.I)})
    if meta2 and meta2.get("content"):
        return meta2["content"].lower().split("-")[0][:2]
    return "en"


def get_shipping_critical(lang: str) -> dict:
    return SHIPPING_CRITICAL_BY_LANG.get(lang, SHIPPING_CRITICAL_BY_LANG["en"])


def get_refund_critical(lang: str) -> dict:
    return REFUND_CRITICAL_BY_LANG.get(lang, REFUND_CRITICAL_BY_LANG["en"])


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
    """Fetch a policy page. No Playwright — policy pages are plain HTML, no JS needed.
    Uses httpx first, ScraperAPI residential proxy as fallback if blocked."""
    try:
        resp = await client.get(url, timeout=10, follow_redirects=True)
        if resp.status_code == 200:
            return resp.text
        # Blocked by Cloudflare/WAF — try ScraperAPI residential proxy
        if resp.status_code in {403, 429} and api_key:
            try:
                r2 = await client.get(scraperapi_url(url, api_key), timeout=30, follow_redirects=True)
                if r2.status_code == 200:
                    return r2.text
            except Exception:
                pass
        return None
    except httpx.RequestError:
        if api_key:
            try:
                r2 = await client.get(scraperapi_url(url, api_key), timeout=30, follow_redirects=True)
                if r2.status_code == 200:
                    return r2.text
            except Exception:
                pass
        return None


NAV_KEYWORDS = {
    "refund":   ["refund", "return", "rückgabe", "erstattung", "retour", "retoure", "remboursement",
                 "devolucion", "terugkeer", "widerruf", "rücknahme"],
    "shipping": ["shipping", "versand", "livraison", "envio", "verzending", "delivery", "leveringen"],
    "contact":  ["contact", "kontakt", "kontaktiere", "contactez", "contacto", "contacteer",
                 "reach us", "get in touch", "support", "hilfe"],
    "about":    ["about", "über uns", "uber-uns", "ueber-uns", "qui sommes", "quienes", "over ons",
                 "notre histoire", "our story", "company", "story", "brand", "who-we", "who we",
                 "mission", "team"],
    "privacy":  ["privacy", "datenschutz", "confidentialite", "privacidad", "privacybeleid",
                 "cookie", "gdpr"],
    "tos":      ["terms", "agb", "conditions", "condiciones", "voorwaarden", "nutzungsbedingungen"],
    "faq":      ["faq", "frequently", "häufig", "questions", "help", "hilfe"],
}

_nav_cache: dict = {}        # base_url → discovered page paths
_page_cache: dict = {}      # full_url → html content (pre-fetched before gather)


PAGE_CATEGORY_KEYWORDS = {
    "refund":   ["refund", "return", "rückgabe", "erstattung", "retour", "retoure",
                 "remboursement", "devolución", "terugkeer", "widerruf", "ruckgabe"],
    "shipping": ["shipping", "versand", "livraison", "envio", "verzending", "delivery",
                 "lieferung", "versandpolitik", "bezorging"],
    "contact":  ["contact", "kontakt", "kontaktiere", "contactez", "contacto",
                 "contacteer", "reach-us", "get-in-touch", "support"],
    "about":    ["about", "uber-uns", "ueber-uns", "uber_uns", "qui-sommes", "quienes",
                 "over-ons", "notre-histoire", "our-story", "story", "company", "brand",
                 "who-we", "mission", "team"],
    "privacy":  ["privacy", "datenschutz", "confidentialite", "privacidad",
                 "privacybeleid", "datenschutzrichtlinie", "cookie"],
    "tos":      ["terms", "agb", "conditions", "condiciones", "voorwaarden",
                 "servicebedingungen", "nutzungsbedingungen"],
    "faq":      ["faq", "frequently", "haufig", "häufig", "questions", "help",
                 "hilfe", "veelgestelde"],
}


async def _discover_via_shopify_api(client, base_url, api_key=None) -> dict[str, str]:
    """Use Shopify /pages.json to get all store pages — falls back to ScraperAPI if blocked."""
    try:
        resp = await client.get(f"{base_url}/pages.json?limit=250", timeout=10)
        # If blocked (429/403), retry via ScraperAPI
        if resp.status_code in {429, 403} and api_key:
            resp = await client.get(scraperapi_url(f"{base_url}/pages.json?limit=250", api_key), timeout=30)
        if resp.status_code != 200:
            return {}
        pages = resp.json().get("pages", [])
        discovered: dict[str, str] = {}
        for page in pages:
            handle = page.get("handle", "").lower()
            title = page.get("title", "").lower()
            combined = f"{handle} {title}"
            for category, keywords in PAGE_CATEGORY_KEYWORDS.items():
                if category not in discovered:
                    if any(kw in combined for kw in keywords):
                        discovered[category] = f"/pages/{page['handle']}"
        return discovered
    except Exception:
        return {}


async def _discover_via_nav_scrape(client, base_url, api_key) -> dict[str, str]:
    """Fallback: scrape homepage nav links for page discovery."""
    html = await fetch_page(client, base_url, api_key)
    if not html:
        return {}

    soup = BeautifulSoup(html, "html.parser")
    discovered: dict[str, str] = {}

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()
        text = a.get_text(strip=True).lower()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        if href.startswith("http") and base_url not in href:
            continue
        path = href if href.startswith("/") else ("/" + href.split(base_url, 1)[-1].lstrip("/"))
        combined = (path + " " + text).lower()
        for category, keywords in PAGE_CATEGORY_KEYWORDS.items():
            if category not in discovered:
                if any(kw in combined for kw in keywords):
                    discovered[category] = path

    return discovered


async def discover_nav_pages(client, base_url, api_key=None) -> dict[str, str]:
    """Discover store pages. Uses Shopify API first (fast, no IP issues), nav scrape as fallback."""
    if base_url in _nav_cache:
        return _nav_cache[base_url]

    # Primary: Shopify pages.json API (fast, always works, any language)
    discovered = await _discover_via_shopify_api(client, base_url, api_key)

    # Fallback: nav scrape (for non-Shopify or if API returns nothing useful)
    if len(discovered) < 3:
        nav = await _discover_via_nav_scrape(client, base_url, api_key)
        for k, v in nav.items():
            if k not in discovered:
                discovered[k] = v

    # Only cache if we found something — never cache empty results (avoids stale empty cache on restart)
    if discovered:
        _nav_cache[base_url] = discovered
    return discovered


async def fetch_first_available(client, base_url, paths, api_key=None, nav_category=None):
    """Fetch first available page. Uses pre-fetched page cache to avoid duplicate requests."""

    def _get_cached(url: str):
        return _page_cache.get(url)

    async def _fetch_with_cache(url: str):
        if url in _page_cache:
            return _page_cache[url]
        html = await fetch_page(client, url, api_key)
        if html:
            _page_cache[url] = html
        return html

    # Try nav-discovered URL first
    if nav_category:
        nav = await discover_nav_pages(client, base_url, api_key)
        discovered_path = nav.get(nav_category)
        if discovered_path:
            url = base_url + discovered_path
            html = _get_cached(url) or await _fetch_with_cache(url)
            if html:
                text = BeautifulSoup(html, "html.parser").get_text()
                if len(text.strip()) > 200:
                    return html, url

    # Fall back to predefined paths
    for path in paths:
        url = base_url + path
        html = _get_cached(url) or await _fetch_with_cache(url)
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
    html, url = await fetch_first_available(client, base_url, SHIPPING_PATHS, api_key, nav_category="shipping")

    if not html:
        default_critical = list(get_shipping_critical("en").keys())
        return {
            "status": "FAIL", "url": None,
            "explanation": "Shipping policy page not found at expected URLs.",
            "critical_missing": default_critical,
            "recommended_missing": list(SHIPPING_RECOMMENDED.keys()),
        }

    text = BeautifulSoup(html, "html.parser").get_text()
    lang = detect_language(html)
    critical_patterns = get_shipping_critical(lang)
    critical_found = check_fields(text, critical_patterns)
    recommended_found = check_fields(text, SHIPPING_RECOMMENDED)

    critical_missing = [f for f, v in critical_found.items() if not v]
    recommended_missing = [f for f, v in recommended_found.items() if not v]

    if critical_missing:
        status = "FAIL"
        missing_labels = ", ".join(FIELD_LABELS[f] for f in critical_missing)
        explanation = f"Critical fields missing: {missing_labels}."
    elif recommended_missing:
        status = "WARNING"
        missing_labels = ", ".join(FIELD_LABELS[f] for f in recommended_missing)
        explanation = f"Recommended fields missing: {missing_labels}."
    else:
        status = "PASS"
        explanation = "Shipping policy contains all required and recommended GMC fields."

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
        return {"status": "PASS", "explanation": "One shipping policy page found.", "duplicates": []}

    urls = list(pages.keys())
    duplicates = []
    for i in range(len(urls)):
        for j in range(i + 1, len(urls)):
            sim = content_similarity(pages[urls[i]], pages[urls[j]])
            if sim > 0.75:
                duplicates.append({"url_1": urls[i], "url_2": urls[j], "similarity": round(sim * 100)})

    if duplicates:
        return {"status": "FAIL",
                "explanation": f"{len(duplicates)} duplicate shipping policy page(s) found. GMC expects one definitive page.",
                "duplicates": duplicates}

    return {"status": "PASS", "explanation": "Multiple shipping pages with unique content found.", "duplicates": []}


async def check_refund_policy(client, base_url, api_key=None) -> dict:
    html, url = await fetch_first_available(client, base_url, REFUND_PATHS, api_key, nav_category="refund")

    if not html:
        default_critical = list(get_refund_critical("en").keys())
        return {
            "status": "FAIL", "url": None,
            "explanation": "Refund/return policy page not found.",
            "critical_missing": default_critical,
            "recommended_missing": list(REFUND_RECOMMENDED.keys()),
        }

    text = BeautifulSoup(html, "html.parser").get_text()
    lang = detect_language(html)
    critical_patterns = get_refund_critical(lang)
    critical_found = check_fields(text, critical_patterns)
    recommended_found = check_fields(text, REFUND_RECOMMENDED)

    critical_missing = [f for f, v in critical_found.items() if not v]
    recommended_missing = [f for f, v in recommended_found.items() if not v]

    if critical_missing:
        status = "FAIL"
        missing_labels = ", ".join(FIELD_LABELS[f] for f in critical_missing)
        explanation = f"Critical fields missing: {missing_labels}."
    elif recommended_missing:
        status = "WARNING"
        missing_labels = ", ".join(FIELD_LABELS[f] for f in recommended_missing)
        explanation = f"Recommended fields missing: {missing_labels}."
    else:
        status = "PASS"
        explanation = "Return policy contains all required and recommended GMC fields."

    return {
        "status": status, "url": url, "explanation": explanation,
        "critical_found": [f for f, v in critical_found.items() if v],
        "critical_missing": [FIELD_LABELS[f] for f in critical_missing],
        "recommended_found": [f for f, v in recommended_found.items() if v],
        "recommended_missing": [FIELD_LABELS[f] for f in recommended_missing],
    }


PRIVACY_PATHS = ["/policies/privacy-policy", "/pages/privacy-policy", "/privacy-policy", "/privacy", "/pages/privacy"]
PRIVACY_CRITICAL = ["collect", "personal", "data", "information"]
PRIVACY_RECOMMENDED = ["cookie", "third party", "gdpr", "contact"]

TOS_PATHS = ["/policies/terms-of-service", "/pages/terms-of-service", "/terms-of-service", "/terms", "/pages/terms", "/policies/terms"]
TOS_CRITICAL = ["terms", "agreement", "service"]

ABOUT_PATHS = ["/pages/about-us", "/pages/about", "/about-us", "/about", "/pages/our-story", "/pages/story",
               "/pages/brand", "/pages/our-brand", "/pages/company", "/pages/team", "/pages/mission",
               "/pages/who-we-are", "/pages/who-we"]
CONTACT_CHECK_PATHS = ["/pages/contact", "/pages/contact-us", "/contact", "/contact-us", "/pages/support"]
FAQ_PATHS = ["/pages/faq", "/pages/faqs", "/faq", "/pages/frequently-asked-questions", "/pages/help"]


async def check_privacy_policy(client, base_url, api_key=None) -> dict:
    html, url = await fetch_first_available(client, base_url, PRIVACY_PATHS, api_key, nav_category="privacy")
    if not html:
        return {"status": "FAIL", "url": None,
                "explanation": "Privacy Policy page not found. GMC requires a privacy policy disclosing data collection."}
    text = BeautifulSoup(html, "html.parser").get_text(separator=" ").lower()
    missing_critical = [f for f in PRIVACY_CRITICAL if f not in text]
    missing_rec = [f for f in PRIVACY_RECOMMENDED if f not in text]
    if missing_critical:
        return {"status": "WARNING", "url": url,
                "explanation": f"Privacy Policy found but missing key content: {', '.join(missing_critical)}."}
    if missing_rec:
        return {"status": "WARNING", "url": url,
                "explanation": f"Privacy Policy present but missing recommended sections: {', '.join(missing_rec)}."}
    return {"status": "PASS", "url": url,
            "explanation": "Privacy Policy found with required data collection disclosures."}


async def check_terms_of_service(client, base_url, api_key=None) -> dict:
    html, url = await fetch_first_available(client, base_url, TOS_PATHS, api_key, nav_category="tos")
    if not html:
        return {"status": "WARNING", "url": None,
                "explanation": "Terms of Service page not found. Recommended by GMC for store credibility."}
    text = BeautifulSoup(html, "html.parser").get_text(separator=" ").lower()
    missing = [f for f in TOS_CRITICAL if f not in text]
    if missing:
        return {"status": "WARNING", "url": url,
                "explanation": f"Terms of Service found but appears incomplete (missing: {', '.join(missing)})."}
    return {"status": "PASS", "url": url,
            "explanation": "Terms of Service found and contains required content."}


async def check_about_us(client, base_url, api_key=None) -> dict:
    html, url = await fetch_first_available(client, base_url, ABOUT_PATHS, api_key, nav_category="about")
    if not html:
        return {"status": "WARNING", "url": None,
                "explanation": "About Us page not found. Adds trust signals for GMC reviewers."}
    text = BeautifulSoup(html, "html.parser").get_text(separator=" ")
    if len(text.strip()) < 150:
        return {"status": "WARNING", "url": url,
                "explanation": "About Us page found but appears very thin (less than 150 chars). Add your story/company info."}
    return {"status": "PASS", "url": url,
            "explanation": "About Us page found with sufficient content."}


async def check_contact_page(client, base_url, api_key=None) -> dict:
    html, url = await fetch_first_available(client, base_url, CONTACT_CHECK_PATHS, api_key, nav_category="contact")
    if not html:
        return {"status": "FAIL", "url": None,
                "explanation": "Contact page not found. GMC requires a way for customers to reach you."}
    text = BeautifulSoup(html, "html.parser").get_text(separator=" ")
    emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6}(?=[^a-zA-Z0-9]|$)", text)
    has_form = bool(re.search(r"<form|<input", html, re.IGNORECASE))
    if emails:
        return {"status": "PASS", "url": url,
                "explanation": f"Contact page found with email address ({emails[0]})."}
    if has_form:
        return {"status": "WARNING", "url": url,
                "explanation": "Contact page found with form but no visible email address. Adding a direct email improves trust."}
    return {"status": "WARNING", "url": url,
            "explanation": "Contact page found but no email or form detected."}


async def check_faq(client, base_url, api_key=None) -> dict:
    html, url = await fetch_first_available(client, base_url, FAQ_PATHS, api_key, nav_category="faq")
    if not html:
        return {"status": "WARNING", "url": None,
                "explanation": "FAQ page not found. Recommended to address shipping/return questions proactively."}
    text = BeautifulSoup(html, "html.parser").get_text(separator=" ")
    if len(text.strip()) < 200:
        return {"status": "WARNING", "url": url,
                "explanation": "FAQ page found but appears very thin. Add shipping, return, and delivery questions."}
    return {"status": "PASS", "url": url,
            "explanation": "FAQ page found with content."}


# ---------------------------------------------------------------------------
# Google Misrepresentation Checklist — 4 additional checks
# ---------------------------------------------------------------------------

PHONE_PATTERN = re.compile(
    r'(\+?\d[\d\s\-\.\(\)]{6,17}\d)',
)
ADDRESS_KEYWORDS = [
    "street", "avenue", "road", "lane", "boulevard", "drive", "straat", "weg",
    "laan", "plein", "steenweg", "postbus", r"p\.o\. box", "po box",
    r"\b\d{4,6}\s+[a-z]{2,}\b",  # Dutch/EU postal codes like "1234 AB"
    r"\b[a-z]{2,}\s+\d{4,6}\b",  # postal code after city
]
PAYMENT_KEYWORDS = [
    "visa", "mastercard", "paypal", "ideal", "klarna", "afterpay", "american express",
    "amex", "maestro", "bancontact", "sofort", "apple pay", "google pay",
    "sepa", "przelewy", "diners", "discover",
]
REFUND_CONTENT_SECTIONS = {
    "cancellation period": [r"\d+\s*(day|dagen|werkdag|business day)", "cancel", "cancellation period", "retourperiode", "retour binnen"],
    "refund method": ["refund to", "original payment", "store credit", "terugbetaal", "creditcard", "same payment"],
    "damaged goods": ["damaged", "defective", "incorrect", "wrong item", "beschadigd", "defect", "verkeerd"],
    "return procedure": ["email", "contact", "form", "portal", "procedure", "how to return", "retour aanvragen", "stap"],
    "shipping costs": ["shipping cost", "verzendkosten", "postage", "free return", "gratis retour", "at your own cost"],
}


async def check_contact_info_completeness(client, base_url, api_key=None) -> dict:
    """Google requires at least 2 of: physical address, phone, email on Contact + Refund pages."""
    html, url = await fetch_first_available(client, base_url, CONTACT_CHECK_PATHS, api_key, nav_category="contact")
    if not html:
        return {"status": "FAIL", "url": None,
                "explanation": "Contact page not found. Google requires physical address, phone, or email."}

    text = BeautifulSoup(html, "html.parser").get_text(separator=" ")

    # Check for email
    emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,6}(?=[^a-zA-Z0-9]|$)", text)
    has_email = bool(emails)

    # Check for phone number
    phones = PHONE_PATTERN.findall(text)
    has_phone = bool([p for p in phones if len(re.sub(r'\D', '', p)) >= 7])

    # Check for physical address
    has_address = False
    for kw in ADDRESS_KEYWORDS:
        try:
            if re.search(kw, text, re.IGNORECASE):
                has_address = True
                break
        except re.error:
            if kw.lower() in text.lower():
                has_address = True
                break

    found = sum([has_email, has_phone, has_address])
    details = []
    if has_email: details.append("email ✓")
    if has_phone: details.append("phone ✓")
    if has_address: details.append("address ✓")
    missing = []
    if not has_email: missing.append("email")
    if not has_phone: missing.append("phone number")
    if not has_address: missing.append("physical address")

    if found >= 2:
        return {"status": "PASS", "url": url,
                "explanation": f"Contact page has {found}/3 required contact methods: {', '.join(details)}."}
    if found == 1:
        return {"status": "WARNING", "url": url,
                "explanation": f"Contact page only has {', '.join(details)}. Google requires at least 2 of: address, phone, email. Missing: {', '.join(missing)}."}
    return {"status": "FAIL", "url": url,
            "explanation": f"Contact page missing all required contact info. Add at least 2 of: physical address, phone number, email address."}


async def check_refund_in_footer(client, base_url, api_key=None) -> dict:
    """Refund/return policy must be linked from the homepage footer."""
    html, url = await fetch_first_available(client, base_url, ["/"], api_key)
    if not html:
        html = await fetch_page(client, base_url, api_key)
    if not html:
        return {"status": "WARNING", "url": base_url,
                "explanation": "Could not fetch homepage to check footer links."}

    soup = BeautifulSoup(html, "html.parser")
    footer = soup.find("footer") or soup.find(id=re.compile("footer", re.I)) or soup.find(class_=re.compile("footer", re.I))
    search_area = footer or soup  # fallback to full page if no footer tag

    links = search_area.find_all("a", href=True)
    for link in links:
        href = (link.get("href") or "").lower()
        text = link.get_text(strip=True).lower()
        if any(kw in href or kw in text for kw in [
            "refund", "return", "retour", "terugkeer",          # EN/NL
            "rückgabe", "erstattung", "ruckkehr", "ruckgabe",   # DE
            "remboursement", "retourner",                        # FR
            "devolución", "devolucion",                          # ES
            "retoure", "widerruf",                               # DE alt
        ]):
            return {"status": "PASS", "url": base_url,
                    "explanation": f"Return/refund policy linked in footer (\"{link.get_text(strip=True)}\")."}

    return {"status": "FAIL", "url": base_url,
            "explanation": "No link to return/refund policy found in footer. Google requires this to be visible on the homepage."}


async def check_refund_policy_quality(client, base_url, api_key=None) -> dict:
    """Check refund policy for required content sections per Google's checklist."""
    html, url = await fetch_first_available(client, base_url, REFUND_PATHS, api_key, nav_category="refund")
    if not html:
        return {"status": "FAIL", "url": None,
                "explanation": "Refund policy not found — content quality could not be assessed."}

    text = BeautifulSoup(html, "html.parser").get_text(separator=" ").lower()
    missing_sections = []

    for section, patterns in REFUND_CONTENT_SECTIONS.items():
        found = any(
            bool(re.search(p, text, re.IGNORECASE) if p.startswith(r'\d') or p.startswith(r'\b') else (p in text))
            for p in patterns
        )
        if not found:
            missing_sections.append(section)

    if not missing_sections:
        return {"status": "PASS", "url": url,
                "explanation": "Refund policy covers all required sections: cancellation period, refund method, damaged goods, return procedure, shipping costs."}
    if len(missing_sections) <= 2:
        return {"status": "WARNING", "url": url,
                "explanation": f"Refund policy missing {len(missing_sections)} section(s): {', '.join(missing_sections)}.",
                "items": [{"text": s} for s in missing_sections]}
    return {"status": "FAIL", "url": url,
            "explanation": f"Refund policy is incomplete — missing {len(missing_sections)}/5 required sections: {', '.join(missing_sections)}.",
            "items": [{"text": s} for s in missing_sections]}


async def check_payment_methods_visible(client, base_url, api_key=None) -> dict:
    """Check if payment method logos/names are visible on the homepage."""
    html = await fetch_page(client, base_url, api_key)
    if not html:
        # try with trailing slash
        html = await fetch_page(client, base_url + "/", api_key)
    if not html:
        return {"status": "WARNING", "url": base_url,
                "explanation": "Could not fetch homepage to check payment methods."}

    soup = BeautifulSoup(html, "html.parser")
    # Check text + img src/alt for payment keywords
    page_text = soup.get_text(separator=" ").lower()
    img_srcs = " ".join((img.get("src", "") + " " + img.get("alt", "")).lower() for img in soup.find_all("img"))
    combined = page_text + " " + img_srcs

    found = [kw for kw in PAYMENT_KEYWORDS if kw in combined]
    if len(found) >= 2:
        return {"status": "PASS", "url": base_url,
                "explanation": f"Payment methods visible on homepage: {', '.join(found[:5])}."}
    if len(found) == 1:
        return {"status": "WARNING", "url": base_url,
                "explanation": f"Only 1 payment method visible ({found[0]}). Add payment icons to footer for customer trust."}
    return {"status": "WARNING", "url": base_url,
            "explanation": "No payment method logos or names detected on homepage. Add Visa/Mastercard/PayPal icons to footer."}


async def check_customer_service_hours(client, base_url, api_key=None) -> dict:
    html, url = await fetch_first_available(client, base_url, CONTACT_PATHS, api_key, nav_category="contact")

    if not html:
        return {"status": "WARNING", "url": None,
                "explanation": "Contact page not found. Customer service hours could not be verified."}

    text = BeautifulSoup(html, "html.parser").get_text()
    hours_found = any(re.search(p, text, re.IGNORECASE) for p in HOURS_PATTERNS)

    if hours_found:
        return {"status": "PASS", "url": url,
                "explanation": "Customer service hours found on contact page."}
    return {"status": "WARNING", "url": url,
            "explanation": "Contact page found but no service hours detected. Add when customers can reach you."}


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

    timeout_result = {"status": "WARNING", "explanation": "Policy check timed out.", "duplicates": []}

    async with httpx.AsyncClient(headers={"User-Agent": HUMAN_UA}, follow_redirects=True) as client:
        # Pre-fetch nav pages ONCE — prevents 13 concurrent homepage fetches (race condition)
        try:
            nav_pages = await asyncio.wait_for(
                discover_nav_pages(client, base_url, api_key), timeout=60
            )
        except Exception:
            nav_pages = {}
        # Populate cache so all checks reuse it — only if non-empty to avoid poisoning cache
        if nav_pages:
            _nav_cache[base_url] = nav_pages

        # Pre-fetch all discovered pages in parallel — eliminates duplicate requests
        # Stores that return 429 will go through ScraperAPI once per URL, not 13 times
        if nav_pages:
            fetch_tasks = [
                fetch_page(client, base_url + path, api_key)
                for path in nav_pages.values()
                if path.startswith("/")
            ]
            # Also pre-fetch homepage for footer/payment checks
            fetch_tasks.append(fetch_page(client, base_url + "/", api_key))
            try:
                results_html = await asyncio.wait_for(
                    asyncio.gather(*fetch_tasks, return_exceptions=True), timeout=60
                )
                # Populate page cache
                paths_to_prefetch = list(nav_pages.values()) + ["/"]
                for path, html in zip(paths_to_prefetch, results_html):
                    if isinstance(html, str) and html:
                        _page_cache[base_url + path] = html
            except Exception:
                pass  # Best effort — checks will fall back to live fetch

        try:
            (shipping, duplicate, refund, hours, privacy, tos, about, contact, faq,
             contact_completeness, refund_footer, refund_quality, payment_methods) = await asyncio.wait_for(
                asyncio.gather(
                    check_shipping_policy(client, base_url, api_key),
                    check_duplicate_shipping_policy(client, base_url, api_key),
                    check_refund_policy(client, base_url, api_key),
                    check_customer_service_hours(client, base_url, api_key),
                    check_privacy_policy(client, base_url, api_key),
                    check_terms_of_service(client, base_url, api_key),
                    check_about_us(client, base_url, api_key),
                    check_contact_page(client, base_url, api_key),
                    check_faq(client, base_url, api_key),
                    check_contact_info_completeness(client, base_url, api_key),
                    check_refund_in_footer(client, base_url, api_key),
                    check_refund_policy_quality(client, base_url, api_key),
                    check_payment_methods_visible(client, base_url, api_key),
                ),
                timeout=90,
            )
        except asyncio.TimeoutError:
            shipping = duplicate = refund = hours = privacy = tos = about = contact = faq = \
                contact_completeness = refund_footer = refund_quality = payment_methods = {**timeout_result}
        finally:
            # Clear cache entries after scan to avoid stale data
            _nav_cache.pop(base_url, None)
            for url in list(_page_cache.keys()):
                if base_url in url:
                    _page_cache.pop(url, None)

    statuses = [shipping["status"], duplicate["status"], refund["status"], hours["status"],
                privacy["status"], tos["status"], about["status"], contact["status"], faq["status"],
                contact_completeness["status"], refund_footer["status"], refund_quality["status"],
                payment_methods["status"]]
    overall = "FAIL" if "FAIL" in statuses else "WARNING" if "WARNING" in statuses else "PASS"

    return {
        "store_url": store_url,
        "overall_policy_status": overall,
        "checks": {
            "shipping_policy": shipping,
            "duplicate_shipping": duplicate,
            "refund_policy": refund,
            "customer_service_hours": hours,
            "privacy_policy": privacy,
            "terms_of_service": tos,
            "about_us": about,
            "contact_page": contact,
            "faq": faq,
            "contact_info_completeness": contact_completeness,
            "refund_in_footer": refund_footer,
            "refund_policy_quality": refund_quality,
            "payment_methods": payment_methods,
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

