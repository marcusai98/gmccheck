import asyncio
import json
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

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="GMC Compliance Check")
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


def ensure_url(url: str) -> str:
    url = url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL parameter is required")
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url


async def scan_steps(store_url: str) -> AsyncGenerator[Dict[str, Any], None]:
    steps = [
        ("trust", run_trust_checks),
        ("links", run_link_check),
        ("policies", run_policy_checks),
        ("products", run_product_checks),
        ("images", run_image_checks),
    ]

    step_results: Dict[str, Any] = {}

    for step_name, func in steps:
        try:
            result = await func(store_url)
            step_results[step_name] = result
            yield {
                "type": "progress",
                "step": step_name,
                "status": "done",
                "result": result,
            }
        except Exception as exc:  # pragma: no cover - defensive
            yield {
                "type": "error",
                "step": step_name,
                "message": str(exc),
            }
            return

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

    yield {
        "type": "complete",
        "report": combined,
    }


@app.get("/api/scan/stream")
async def stream_scan(url: str):
    store_url = ensure_url(url)

    async def event_publisher() -> AsyncGenerator[Dict[str, str], None]:
        async for event in scan_steps(store_url):
            yield {"data": json.dumps(event)}

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
    return EventSourceResponse(event_publisher(), headers=headers)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("serve:app", host="0.0.0.0", port=8082, reload=False)
