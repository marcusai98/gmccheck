import asyncio
import json
import math

class SafeEncoder(json.JSONEncoder):
    """Convert numpy/non-standard types to JSON-safe Python types."""
    def default(self, obj):
        try:
            import numpy as np
            if isinstance(obj, (np.integer,)): return int(obj)
            if isinstance(obj, (np.floating,)): return float(obj)
            if isinstance(obj, np.ndarray): return obj.tolist()
        except ImportError:
            pass
        if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
            return None
        return super().default(obj)
from pathlib import Path
from typing import AsyncGenerator, Dict, Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from gmc_scanner import calculate_score, extract_all_checks, format_report
from trust_checks import run_trust_checks
from link_checker import run_link_check
from policy_scraper import run_policy_checks
from product_checker import run_product_checks
from image_checker import run_image_checks
from database import init_db, save_scan, get_recent_scans, get_scan_by_id, get_scans_for_domain

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="GMC Compliance Check")

@app.on_event("startup")
async def startup():
    init_db()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")


@app.get("/", response_class=FileResponse)
async def serve_frontend() -> FileResponse:
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(index_path)


@app.get("/health")
async def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/api/history")
async def history(limit: int = 20):
    return {"scans": get_recent_scans(limit)}


@app.get("/api/history/{scan_id}")
async def scan_detail(scan_id: int):
    scan = get_scan_by_id(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@app.get("/api/history/domain/{domain}")
async def domain_history(domain: str, limit: int = 10):
    return {"scans": get_scans_for_domain(domain, limit)}


def ensure_url(url: str) -> str:
    url = url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL parameter is required")
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url


async def scan_steps(store_url: str) -> AsyncGenerator[Dict[str, Any], None]:
    steps = [
        ("trust",    run_trust_checks,   60),
        ("links",    run_link_check,      90),
        ("policies", run_policy_checks,  100),
        ("products", run_product_checks, 100),
        ("images",   run_image_checks,    70),
    ]

    step_results: Dict[str, Any] = {}

    for step_name, func, step_timeout in steps:
        try:
            result = await asyncio.wait_for(func(store_url), timeout=step_timeout)
            step_results[step_name] = result
            yield {
                "type": "progress",
                "step": step_name,
                "status": "done",
                "result": result,
            }
        except asyncio.TimeoutError:
            step_results[step_name] = {"status": "WARNING", "explanation": f"{step_name.capitalize()} check timed out after {step_timeout}s."}
            yield {"type": "progress", "step": step_name, "status": "done", "result": step_results[step_name]}
        except Exception as exc:
            step_results[step_name] = {}
            yield {"type": "progress", "step": step_name, "status": "done", "result": {}}

    combined = {
        "store_url": store_url,
        "trust": step_results.get("trust"),
        "links": step_results.get("links"),
        "policies": step_results.get("policies"),
        "products": step_results.get("products"),
        "images": step_results.get("images"),
    }

    all_checks = extract_all_checks(combined)
    score = calculate_score(all_checks)
    summary = format_report(store_url, combined, all_checks, score)

    combined["all_checks"] = all_checks
    combined["score"] = score
    combined["summary"] = summary

    # Persist scan to SQLite
    scan_id = save_scan(store_url, score, combined)
    combined["scan_id"] = scan_id

    yield {
        "type": "complete",
        "report": combined,
    }


@app.get("/api/scan/stream")
async def stream_scan(url: str):
    store_url = ensure_url(url)

    async def event_publisher() -> AsyncGenerator[Dict[str, str], None]:
        async for event in scan_steps(store_url):
            yield {"data": json.dumps(event, cls=SafeEncoder)}

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
    return EventSourceResponse(event_publisher(), headers=headers)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("serve:app", host="0.0.0.0", port=8082, reload=False)
