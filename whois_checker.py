"""
GMC Compliance Agent — whois Domain Checker
============================================
Checks domain age, registrar, expiry and privacy shield status.

Usage:
    import asyncio
    from whois_checker import run_whois_check

    results = asyncio.run(run_whois_check("https://realsabai.com"))

Returns a dict ready to merge into the agent's scan context object.
"""

import asyncio
from datetime import datetime, timezone
from urllib.parse import urlparse

import whois


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

AGE_FAIL_DAYS    = 30    # < 30 days → FAIL
AGE_WARNING_DAYS = 90    # < 90 days → WARNING


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_domain(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    return urlparse(url).netloc.lower().lstrip("www.")


def normalise_date(val) -> datetime | None:
    """whois returns dates as datetime, list of datetimes, or None."""
    if val is None:
        return None
    if isinstance(val, list):
        val = val[0]
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val
    return None


def days_since(dt: datetime) -> int:
    now = datetime.now(timezone.utc)
    return (now - dt).days


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_whois_check(store_url: str) -> dict:
    """
    Run whois lookup for a store domain.

    Args:
        store_url: e.g. "https://realsabai.com"

    Returns:
        Structured dict for agent scan context.
    """
    domain = get_domain(store_url)

    try:
        # whois is blocking — run in thread pool with hard timeout
        loop = asyncio.get_event_loop()
        w = await asyncio.wait_for(
            loop.run_in_executor(None, whois.whois, domain),
            timeout=12
        )
    except Exception as e:
        return {
            "domain": domain,
            "status": "ERROR",
            "error": str(e),
            "domain_age_days": None,
            "creation_date": None,
            "expiry_date": None,
            "registrar": None,
            "privacy_protected": None,
        }

    creation_date = normalise_date(w.creation_date)
    expiry_date   = normalise_date(w.expiration_date)
    registrar     = w.registrar if isinstance(w.registrar, str) else (
        w.registrar[0] if isinstance(w.registrar, list) else None
    )

    # Privacy / proxy detection
    privacy_keywords = ["privacy", "proxy", "whoisguard", "redacted", "protect", "withheld"]
    registrant = str(w.get("registrant_name", "") or "").lower()
    privacy_protected = any(k in registrant for k in privacy_keywords)

    if creation_date is None:
        status = "WARNING"
        age_days = None
        explanation = "Creation date not available in whois record."
    else:
        age_days = days_since(creation_date)
        if age_days < AGE_FAIL_DAYS:
            status = "FAIL"
            explanation = (
                f"Domain is only {age_days} days old. "
                "Google Merchant Center typically rejects stores with domains under 30 days old."
            )
        elif age_days < AGE_WARNING_DAYS:
            status = "WARNING"
            explanation = (
                f"Domain is {age_days} days old. "
                "New domains (under 90 days) are flagged as higher risk by GMC reviewers."
            )
        else:
            status = "PASS"
            explanation = f"Domain is {age_days} days old. No age-related issues."

    return {
        "domain": domain,
        "status": status,
        "explanation": explanation,
        "domain_age_days": age_days,
        "creation_date": creation_date.isoformat() if creation_date else None,
        "expiry_date": expiry_date.isoformat() if expiry_date else None,
        "registrar": registrar,
        "privacy_protected": privacy_protected,
        "raw_name_servers": list(w.name_servers or []),
    }


# ---------------------------------------------------------------------------
# CLI — python whois_checker.py realsabai.com
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys, json

    url = sys.argv[1] if len(sys.argv) > 1 else "realsabai.com"
    print(f"\nwhois lookup: {url}\n{'─' * 46}")

    result = asyncio.run(run_whois_check(url))

    print(f"Status:       {result['status']}")
    print(f"Age:          {result['domain_age_days']} days")
    print(f"Created:      {result['creation_date']}")
    print(f"Expires:      {result['expiry_date']}")
    print(f"Registrar:    {result['registrar']}")
    print(f"Privacy:      {result['privacy_protected']}")
    print(f"\nExplanation:  {result.get('explanation', '')}")
    print("\n── Full JSON ──")
    print(json.dumps(result, indent=2))

