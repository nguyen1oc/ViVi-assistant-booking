import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .human_review_errors import HumanReviewError
from .human_review_routes import router

app = FastAPI(
    title="P-053 Human Review API",
    description="Standalone API for independent benchmark labeling.",
    version="1.0.0",
)


@app.exception_handler(HumanReviewError)
async def human_review_error_handler(_request, exc: HumanReviewError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": {"code": exc.code, "message": str(exc)}},
    )


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "human-review"}


app.include_router(router, prefix="/api/v1")

configured_static_root = os.getenv("HUMAN_REVIEW_STATIC_DIR", "").strip()
static_root = (
    Path(configured_static_root).resolve()
    if configured_static_root
    else Path(__file__).resolve().parents[3] / "human-review" / "frontend" / "dist"
)
if (static_root / "index.html").is_file():
    assets_root = static_root / "assets"
    if assets_root.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_root), name="human-review-assets")

    @app.get("/", include_in_schema=False)
    def frontend_index():
        return FileResponse(static_root / "index.html")

    @app.get("/{requested_path:path}", include_in_schema=False)
    def frontend_route(requested_path: str):
        # Never turn an unknown API URL into an HTML success response.
        if requested_path.startswith("api/"):
            return JSONResponse(status_code=404, content={"detail": "Not Found"})
        return FileResponse(static_root / "index.html")
