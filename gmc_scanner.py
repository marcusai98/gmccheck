"""
GMC Compliance Agent — Master Scanner
======================================
Runs alle checks parallel en produceert een volledig GMC compliance rapport.

Usage:
    import asyncio
    from gmc_scanner import run_full_scan

    report = asyncio.run(run_full_scan("https://realsabai.com"))
    print(report["summary"])
"""

import asyncio
import json
from datetime import datetime

from link_checker import run_link_check
from trust_checks import run_trust_checks
from policy_scraper import run_policy_checks
from product_checker import run_product_checks
from image_checker import run_image_checks


# ---------------------------------------------------------------------------
# Score calculator
# ---------------------------------------------------------------------------

# Weight per check — higher = more impact on score
# Critical GMC requirements get weight 3, important get 2, advisory get 1
CHECK_WEIGHTS = {
    "Domain age":                   3,   # GMC suspends young domains
    "ScamAdviser score":            2,
    "Trustpilot score":             1,   # Advisory — not all stores have it
    "Broken links":                 3,   # GMC crawls pages; 404s = suspension risk
    "Wrong-domain links":           1,   # Advisory
    "Email domain mismatch":        1,   # Advisory
    "Shipping policy completeness": 3,   # GMC required
    "Duplicate shipping policy":    2,
    "Refund policy completeness":   3,   # GMC required
    "Customer service hours":       2,
    "Privacy Policy":               3,   # GMC required — data collection disclosure
    "Terms of Service":             2,
    "About Us":                     1,
    "Contact page":                 3,   # GMC requires contact info
    "FAQ page":                     1,
    "Empty collections":            2,
    "Products per collection (min. 5)": 1, # Advisory
    "Duplicate product images":     2,
}
DEFAULT_WEIGHT = 1

def calculate_score(all_checks: list[dict]) -> dict:
    """Calculate overall compliance score from all check results."""
    total = len(all_checks)
    passed = sum(1 for c in all_checks if c["status"] == "PASS")
    failed = sum(1 for c in all_checks if c["status"] == "FAIL")
    warnings = sum(1 for c in all_checks if c["status"] == "WARNING")
    errors = sum(1 for c in all_checks if c["status"] == "ERROR")
    skipped = sum(1 for c in all_checks if c["status"] == "SKIPPED")

    # Weighted score — critical checks count more than advisory ones
    # WARNING counts as 0.4 of a pass (partial credit)
    weighted_score = 0.0
    weighted_total = 0.0
    for c in all_checks:
        if c["status"] == "SKIPPED": continue
        w = CHECK_WEIGHTS.get(c["name"], DEFAULT_WEIGHT)
        weighted_total += w
        if c["status"] == "PASS":      weighted_score += w
        elif c["status"] == "WARNING": weighted_score += w * 0.4
    score_pct = round((weighted_score / weighted_total * 100) if weighted_total > 0 else 0, 1)

    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "warnings": warnings,
        "errors": errors,
        "skipped": skipped,
        "score_pct": score_pct,
    }


# ---------------------------------------------------------------------------
# Flat check extractor
# ---------------------------------------------------------------------------

def extract_all_checks(results: dict) -> list[dict]:
    """Flatten all nested check results into a single list."""
    checks = []

    # Trust checks
    trust = results.get("trust", {})
    checks.append({"name": "Domain age", "category": "Trust",
                   **trust.get("whois", {"status": "ERROR"})})
    checks.append({"name": "ScamAdviser score", "category": "Trust",
                   **trust.get("scamadviser", {"status": "ERROR"})})
    checks.append({"name": "Trustpilot score", "category": "Trust",
                   **trust.get("trustpilot", {"status": "ERROR"})})

    # Link checks
    link = results.get("links", {}).get("checks", {})
    checks.append({"name": "Broken links", "category": "Links",
                   "status": link.get("broken_links", {}).get("status", "ERROR"),
                   "explanation": f"{link.get('broken_links', {}).get('count', 0)} broken link(s) found.",
                   "items": link.get("broken_links", {}).get("items", [])})
    checks.append({"name": "Wrong-domain links", "category": "Links",
                   "status": link.get("wrong_domain_links", {}).get("status", "ERROR"),
                   "explanation": f"{link.get('wrong_domain_links', {}).get('count', 0)} wrong-domain link(s) found.",
                   "items": link.get("wrong_domain_links", {}).get("items", [])})
    checks.append({"name": "Email domain mismatch", "category": "Links",
                   "status": link.get("email_mismatches", {}).get("status", "ERROR"),
                   "explanation": f"{link.get('email_mismatches', {}).get('count', 0)} email mismatch(es) found.",
                   "items": link.get("email_mismatches", {}).get("items", [])})

    # Policy checks
    policy = results.get("policies", {}).get("checks", {})
    checks.append({"name": "Shipping policy completeness", "category": "Policies",
                   **policy.get("shipping_policy", {"status": "ERROR", "explanation": ""})})
    dup = policy.get("duplicate_shipping", {"status": "ERROR", "explanation": ""})
    dup_items = [{"url": d.get("url_1",""), "similarity": d.get("similarity",0)} for d in dup.get("duplicates", [])]
    dup_items += [{"url": d.get("url_2",""), "similarity": d.get("similarity",0)} for d in dup.get("duplicates", []) if d.get("url_2") != d.get("url_1")]
    # Deduplicate URLs
    seen = set(); dup_items_uniq = []
    for d in dup_items:
        if d["url"] not in seen: seen.add(d["url"]); dup_items_uniq.append(d)
    checks.append({"name": "Duplicate shipping policy", "category": "Policies",
                   "status": dup.get("status","ERROR"),
                   "explanation": dup.get("explanation",""),
                   "items": [{"url": d["url"], "status_code": f"{d['similarity']}% match"} for d in dup_items_uniq]})
    checks.append({"name": "Refund policy completeness", "category": "Policies",
                   **policy.get("refund_policy", {"status": "ERROR", "explanation": ""})})
    checks.append({"name": "Customer service hours", "category": "Policies",
                   **policy.get("customer_service_hours", {"status": "ERROR", "explanation": ""})})
    checks.append({"name": "Privacy Policy", "category": "Policies",
                   **policy.get("privacy_policy", {"status": "ERROR", "explanation": ""})})
    checks.append({"name": "Terms of Service", "category": "Policies",
                   **policy.get("terms_of_service", {"status": "ERROR", "explanation": ""})})
    checks.append({"name": "About Us", "category": "Policies",
                   **policy.get("about_us", {"status": "ERROR", "explanation": ""})})
    checks.append({"name": "Contact page", "category": "Policies",
                   **policy.get("contact_page", {"status": "ERROR", "explanation": ""})})
    checks.append({"name": "FAQ page", "category": "Policies",
                   **policy.get("faq", {"status": "ERROR", "explanation": ""})})

    # Product checks
    product = results.get("products", {}).get("checks", {})
    empty = product.get("empty_collections", {})
    checks.append({"name": "Empty collections", "category": "Products",
                   "status": empty.get("status", "ERROR"),
                   "explanation": empty.get("explanation", "")})

    # Per-collection checks — summarise as one check
    col_results = product.get("collections", [])
    if col_results:
        non_pass = [c for c in col_results if c["status"] != "PASS"]
        col_status = "FAIL" if any(c["status"] == "FAIL" for c in col_results) else \
                     "WARNING" if non_pass else "PASS"
        checks.append({
            "name": "Products per collection (min. 5)",
            "category": "Products",
            "status": col_status,
            "explanation": (
                f"{len(non_pass)} of {len(col_results)} collection(s) below the 5-product minimum."
                if non_pass else
                f"All {len(col_results)} collection(s) meet the minimum of 5 products."
            ),
            "details": non_pass,
        })
    else:
        checks.append({"name": "Products per collection (min. 5)", "category": "Products",
                       "status": "WARNING", "explanation": "No collections found."})

    # Image check
    images = results.get("images", {})
    checks.append({"name": "Duplicate product images", "category": "Products",
                   "status": images.get("status", "ERROR"),
                   "explanation": images.get("explanation", "")})

    return checks


# ---------------------------------------------------------------------------
# Report formatter
# ---------------------------------------------------------------------------

def format_report(store_url: str, results: dict, all_checks: list[dict], score: dict) -> str:
    """Format the final compliance report as plain text."""
    lines = []
    now = datetime.now().strftime("%d %B %Y om %H:%M")

    lines.append("=" * 60)
    lines.append("GMC COMPLIANCE RAPPORT")
    lines.append(f"Store: {store_url}")
    lines.append(f"Gescand: {now}")
    lines.append("=" * 60)

    lines.append("\n── COMPLIANCE SCORE ──────────────────────────────────")
    lines.append(f"  Total checks:      {score['total']}")
    lines.append(f"  Passed:            {score['passed']}  ✓")
    lines.append(f"  Failed:            {score['failed']}  ✗")
    lines.append(f"  Warnings:          {score['warnings']}  ⚠")
    lines.append(f"  Errors/Skipped:    {score['errors'] + score['skipped']}")
    lines.append(f"  Pass rate:         {score['score_pct']}%")

    # Store intelligence
    trust = results.get("trust", {})
    whois = trust.get("whois", {})
    sa = trust.get("scamadviser", {})
    tp = trust.get("trustpilot", {})
    lines.append("\n── STORE INTELLIGENCE ────────────────────────────────")
    lines.append(f"  Domain age:        {whois.get('domain_age_days', 'unknown')} days")
    lines.append(f"  Registrar:         {whois.get('registrar', 'unknown')}")
    lines.append(f"  ScamAdviser:       {sa.get('score', 'unknown')}/100")
    lines.append(f"  Trustpilot:        {tp.get('score', 'not found')}/5  ({tp.get('review_count', 0)} reviews)")

    # Group issues by category
    categories = {}
    for check in all_checks:
        cat = check.get("category", "Overig")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(check)

    lines.append("\n── RESULTATEN PER CATEGORIE ──────────────────────────")
    for cat, cat_checks in categories.items():
        lines.append(f"\n  {cat.upper()}")
        for c in cat_checks:
            icon = {"PASS": "✓", "FAIL": "✗", "WARNING": "⚠", "ERROR": "?", "SKIPPED": "–"}.get(c["status"], "?")
            lines.append(f"  {icon} [{c['status']:<7}] {c['name']}")
            if c["status"] in {"FAIL", "WARNING", "ERROR"}:
                explanation = c.get("explanation", "")
                if explanation:
                    lines.append(f"             → {explanation[:120]}")

    # Top issues
    fails = [c for c in all_checks if c["status"] == "FAIL"]
    warnings = [c for c in all_checks if c["status"] == "WARNING"]

    if fails or warnings:
        lines.append("\n── WAT ALS EERSTE TE FIXEN ───────────────────────────")
        priority = (fails + warnings)[:5]
        for i, c in enumerate(priority, 1):
            lines.append(f"  {i}. [{c['status']}] {c['name']}")
            explanation = c.get("explanation", "")
            if explanation:
                lines.append(f"     {explanation[:150]}")

    lines.append("\n" + "=" * 60)
    lines.append("Wil je dat ik fixes opstel voor deze problemen?")
    lines.append("=" * 60)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_full_scan(store_url: str) -> dict:
    """
    Voert alle GMC compliance checks parallel uit.

    Args:
        store_url: e.g. "https://realsabai.com"

    Returns:
        Dict met alle resultaten + formatted rapport string.
    """
    if not store_url.startswith("http"):
        store_url = "https://" + store_url

    print(f"\nStart volledige GMC scan voor: {store_url}")
    print("Fase 1: Trust + Links + Policies + Products parallel uitvoeren...")

    # Run all 5 check groups in parallel
    trust, links, policies, products, images = await asyncio.gather(
        run_trust_checks(store_url),
        run_link_check(store_url),
        run_policy_checks(store_url),
        run_product_checks(store_url),
        run_image_checks(store_url),
        return_exceptions=True,
    )

    # Handle any exceptions gracefully
    def safe(result, name):
        if isinstance(result, Exception):
            print(f"  ⚠ {name} check mislukt: {result}")
            return {"status": "ERROR", "error": str(result)}
        return result

    results = {
        "store_url": store_url,
        "trust": safe(trust, "Trust"),
        "links": safe(links, "Links"),
        "policies": safe(policies, "Policies"),
        "products": safe(products, "Products"),
        "images": safe(images, "Images"),
    }

    print("Fase 2: Resultaten samenvoegen en rapport opstellen...")

    all_checks = extract_all_checks(results)
    score = calculate_score(all_checks)
    report = format_report(store_url, results, all_checks, score)

    results["all_checks"] = all_checks
    results["score"] = score
    results["summary"] = report

    return results


# ---------------------------------------------------------------------------
# CLI — python gmc_scanner.py https://yourstore.com
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    url = sys.argv[1] if len(sys.argv) > 1 else "https://realsabai.com"
    results = asyncio.run(run_full_scan(url))
    print(results["summary"])

