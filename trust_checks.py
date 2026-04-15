"""
GMC Compliance Agent — Trust Checks Runner (v2)
================================================
Parallel runner voor whois + Trustpilot + ScamAdviser.
Geeft ScraperAPI key door aan alle scrapers voor VPS gebruik.

Usage:
    import asyncio, os
    from trust_checks import run_trust_checks

    results = asyncio.run(run_trust_checks(
        "https://maisoncozza.com",
        scraperapi_key=os.getenv("SCRAPERAPI_KEY")
    ))
"""

import asyncio
import os

from whois_checker import run_whois_check
from trustpilot_scraper import run_trustpilot_check
from scamadviser_scraper import run_scamadviser_check


aSYNC_TIMEOUT = 90


async def run_trust_checks(store_url: str, scraperapi_key: str | None = None) -> dict:
    """
    Voert alle drie trust checks parallel uit.

    Args:
        store_url: bijv. "https://maisoncozza.com"
        scraperapi_key: ScraperAPI key voor VPS (of via SCRAPERAPI_KEY env var)
    """
    api_key = scraperapi_key or os.getenv("SCRAPERAPI_KEY")

    whois, trustpilot, scamadviser = await asyncio.gather(
        run_whois_check(store_url),
        run_trustpilot_check(store_url, scraperapi_key=api_key),
        run_scamadviser_check(store_url, scraperapi_key=api_key),
    )

    statuses = [whois.get("status"), trustpilot.get("status"), scamadviser.get("status")]
    if "FAIL" in statuses:
        overall = "FAIL"
    elif "WARNING" in statuses or "ERROR" in statuses:
        overall = "WARNING"
    else:
        overall = "PASS"

    return {
        "store_url": store_url,
        "overall_trust_status": overall,
        "whois": whois,
        "trustpilot": trustpilot,
        "scamadviser": scamadviser,
    }


if __name__ == "__main__":
    import sys, json
    url = sys.argv[1] if len(sys.argv) > 1 else "https://maisoncozza.com"
    key = os.getenv("SCRAPERAPI_KEY")
    print(f"\nTrust checks: {url}  |  ScraperAPI: {'ja' if key else 'NIET INGESTELD'}\n{'─'*50}")
    results = asyncio.run(run_trust_checks(url, scraperapi_key=key))
    print(f"Overall:      {results['overall_trust_status']}")
    print(f"whois:        {results['whois']['status']}  — {results['whois'].get('domain_age_days')} dagen")
    print(f"Trustpilot:   {results['trustpilot']['status']}  — {results['trustpilot'].get('score')}/5")
    print(f"ScamAdviser:  {results['scamadviser']['status']}  — {results['scamadviser'].get('score')}/100")

