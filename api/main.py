from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.config import FRONTEND_DIST, cors_allow_credentials, cors_origins
from api.routes.pitwall import router as pitwall_router


app = FastAPI(
    title="Pit Wall",
    description="WebMCP-powered stock-car race strategy game.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=cors_allow_credentials(),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    pitwall_router,
    prefix="/api/v1/nascar",
)


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/api")
def api_summary():
    return {
        "name": "Pit Wall",
        "status": "ready",
        "webmcp": True,
    }


DIST_DIR = FRONTEND_DIST

if DIST_DIR.exists():
    assets_dir = DIST_DIR / "assets"

    if assets_dir.exists():
        app.mount(
            "/assets",
            StaticFiles(directory=assets_dir),
            name="assets",
        )

    @app.get("/{full_path:path}", include_in_schema=False)
    def frontend(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")

        requested = DIST_DIR / full_path

        if full_path and requested.is_file():
            return FileResponse(requested)

        return FileResponse(DIST_DIR / "index.html")