"""
GMC Compliance Agent — Duplicate Image Checker
===============================================
Downloads primary product images and compares them using
perceptual hashing (pHash) to find visual duplicates.
No Gemini API needed — runs entirely locally.

Usage:
    import asyncio
    from image_checker import run_image_checks

    results = asyncio.run(run_image_checks("https://realsabai.com"))
"""

import asyncio
import io
import json
from urllib.parse import urlparse

import httpx

HUMAN_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# Hamming distance threshold — images with distance <= this are considered duplicates
# 0 = identical, 10 = very similar, 20 = somewhat similar
DUPLICATE_THRESHOLD = 8

# Max products to check (keep scan time reasonable)
MAX_PRODUCTS_TO_CHECK = 40   # Reduced to avoid timeout on large stores
IMAGE_SCAN_TIMEOUT = 60      # seconds total


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_base_url(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def compute_phash(image_bytes: bytes) -> str | None:
    """Compute perceptual hash of an image."""
    try:
        from PIL import Image
        import imagehash
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return str(imagehash.phash(img))
    except Exception:
        return None


def hamming_distance(hash1: str, hash2: str) -> int:
    """Calculate Hamming distance between two hex hash strings."""
    try:
        import imagehash
        h1 = imagehash.hex_to_hash(hash1)
        h2 = imagehash.hex_to_hash(hash2)
        return h1 - h2
    except Exception:
        return 999


async def fetch_json(client: httpx.AsyncClient, url: str) -> dict | list | None:
    try:
        resp = await client.get(url, timeout=12, follow_redirects=True)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


async def fetch_image(
    client: httpx.AsyncClient,
    url: str,
    semaphore: asyncio.Semaphore,
) -> bytes | None:
    """Download image bytes."""
    async with semaphore:
        try:
            # Clean up Shopify CDN URLs — remove size suffixes
            clean_url = url.split("?")[0]
            clean_url = clean_url.replace("_grande", "").replace(
                "_large", "").replace("_medium", "").replace("_small", "")
            resp = await client.get(clean_url, timeout=10, follow_redirects=True)
            if resp.status_code == 200:
                return resp.content
            return None
        except Exception:
            return None


# ---------------------------------------------------------------------------
# Product image collection
# ---------------------------------------------------------------------------

async def get_products_with_images(
    client: httpx.AsyncClient, base_url: str
) -> list[dict]:
    """
    Fetch product list via Shopify JSON API.
    Returns list of {title, handle, url, image_url}.
    """
    products = []
    page = 1

    while len(products) < MAX_PRODUCTS_TO_CHECK:
        data = await fetch_json(
            client,
            f"{base_url}/products.json?limit=250&page={page}"
        )
        if not data or not data.get("products"):
            break

        for p in data["products"]:
            images = p.get("images", [])
            if not images:
                continue
            primary_image = images[0].get("src", "")
            if primary_image:
                products.append({
                    "title": p.get("title", "Unknown"),
                    "handle": p.get("handle", ""),
                    "url": f"{base_url}/products/{p.get('handle', '')}",
                    "image_url": primary_image,
                })

        if len(data["products"]) < 250:
            break
        page += 1

    return products[:MAX_PRODUCTS_TO_CHECK]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def run_image_checks(store_url: str) -> dict:
    """
    Check for duplicate product images using perceptual hashing.

    Args:
        store_url: e.g. "https://realsabai.com"

    Returns:
        Structured dict for agent scan context.
    """
    if not store_url.startswith("http"):
        store_url = "https://" + store_url
    base_url = get_base_url(store_url)

    # Verify imagehash is available
    try:
        import imagehash
        from PIL import Image
    except ImportError:
        return {
            "store_url": store_url,
            "status": "SKIPPED",
            "explanation": "imagehash or Pillow not installed. Run: pip install imagehash Pillow",
            "duplicates": [],
            "products_checked": 0,
        }

    semaphore = asyncio.Semaphore(10)

    async with httpx.AsyncClient(
        headers={"User-Agent": HUMAN_UA}, follow_redirects=True
    ) as client:

        # ── Get product list ──────────────────────────────────────────────
        products = await get_products_with_images(client, base_url)

        if not products:
            return {
                "store_url": store_url,
                "status": "WARNING",
                "explanation": "No products with images found via API.",
                "duplicates": [],
                "products_checked": 0,
            }

        # ── Download all images in parallel ───────────────────────────────
        image_tasks = [
            fetch_image(client, p["image_url"], semaphore)
            for p in products
        ]
        try:
            image_bytes_list = await asyncio.wait_for(
                asyncio.gather(*image_tasks), timeout=IMAGE_SCAN_TIMEOUT
            )
        except asyncio.TimeoutError:
            return {"status": "WARNING", "explanation": "Image scan timed out after 60s — store may have too many products.",
                    "duplicate_count": 0, "total_checked": 0, "duplicates": []}

        # ── Compute perceptual hashes ─────────────────────────────────────
        loop = asyncio.get_event_loop()
        hashes = []
        valid_products = []

        for product, img_bytes in zip(products, image_bytes_list):
            if img_bytes:
                # Run CPU-bound hash in thread pool
                h = await loop.run_in_executor(None, compute_phash, img_bytes)
                if h:
                    hashes.append(h)
                    valid_products.append(product)

        # ── Find duplicates ───────────────────────────────────────────────
        duplicates = []
        for i in range(len(hashes)):
            for j in range(i + 1, len(hashes)):
                dist = hamming_distance(hashes[i], hashes[j])
                if dist <= DUPLICATE_THRESHOLD:
                    duplicates.append({
                        "product_1": {
                            "title": valid_products[i]["title"],
                            "url": valid_products[i]["url"],
                            "image_url": valid_products[i]["image_url"],
                        },
                        "product_2": {
                            "title": valid_products[j]["title"],
                            "url": valid_products[j]["url"],
                            "image_url": valid_products[j]["image_url"],
                        },
                        "similarity_distance": dist,
                        "note": "identical" if dist == 0 else "very similar",
                    })

        # ── Verdict ───────────────────────────────────────────────────────
        if duplicates:
            status = "WARNING"
            explanation = (
                f"Found {len(duplicates)} duplicate image pair(s) across "
                f"{len(valid_products)} products checked. "
                "Duplicate images between products may confuse GMC product matching."
            )
        else:
            status = "PASS"
            explanation = (
                f"No duplicate images found across {len(valid_products)} products checked."
            )

    return {
        "store_url": store_url,
        "status": status,
        "explanation": explanation,
        "products_checked": len(valid_products),
        "duplicates_found": len(duplicates),
        "duplicates": duplicates,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys, json

    url = sys.argv[1] if len(sys.argv) > 1 else "https://realsabai.com"
    print(f"\nImage duplicate check: {url}\n{'─' * 50}")

    results = asyncio.run(run_image_checks(url))

    print(f"Status:           {results['status']}")
    print(f"Products checked: {results['products_checked']}")
    print(f"Duplicates found: {results['duplicates_found']}")
    print(f"Explanation:      {results['explanation']}")

    if results["duplicates"]:
        print("\nDuplicate pairs:")
        for d in results["duplicates"]:
            print(f"  • {d['product_1']['title']} ↔ {d['product_2']['title']} (distance: {d['similarity_distance']})")

    print("\n── Full JSON ──")
    print(json.dumps(results, indent=2))

