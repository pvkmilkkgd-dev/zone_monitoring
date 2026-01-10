from pathlib import Path
import mimetypes

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import admin_users
from app.api.v1.admin_settings import router as admin_settings_router
from app.api.v1.routes.auth import router as auth_router
from app.core.bootstrap import require_bootstrap_completed
from app.routers.users import router as users_router
from app.api.maps import router as maps_router


app = FastAPI(
    title="Zone Monitoring",
    version="0.1.0",
)

@app.get("/ping")
def ping():
    return {"ok": True}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/ping", tags=["default"])
def ping():
    return {"status": "ok"}


# --- API ---
app.include_router(auth_router, prefix="/api/v1")
app.include_router(
    admin_settings_router,
    prefix="/api/v1",
    dependencies=[Depends(require_bootstrap_completed)],
)
app.include_router(users_router, prefix="/api/v1")
app.include_router(admin_users.router)
app.include_router(maps_router)

# --- FRONT (Vite build) ---
PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parent.parent  # .../backend
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
INDEX_FILE = FRONTEND_DIST / "index.html"
FRONTEND_ROOT = PROJECT_ROOT / "frontend"
MAPS_DIR = BACKEND_DIR / "maps"

mimetypes.add_type("application/geo+json", ".geojson")
mimetypes.add_type("application/json", ".json")

# 1) Static assets (Vite)
app.mount(
    "/assets",
    StaticFiles(directory=FRONTEND_DIST / "assets", html=False),
    name="assets",
)

# 1.5) GeoJSON maps
if MAPS_DIR.exists():
    app.mount("/maps", StaticFiles(directory=str(MAPS_DIR)), name="maps")


# 2) Vite icon
@app.get("/vite.svg", include_in_schema=False)
async def vite_svg():
    vite_icon = FRONTEND_DIST / "vite.svg"
    if not vite_icon.exists():
        fallback = FRONTEND_ROOT / "vite.svg"
        if fallback.exists():
            vite_icon = fallback
        else:
            raise HTTPException(status_code=404, detail="vite.svg not found")
    return FileResponse(vite_icon)


# 3) SPA routes: root and /admin -> index.html
@app.get("/", include_in_schema=False)
@app.get("/admin", include_in_schema=False)
@app.get("/admin/{_:path}", include_in_schema=False)
async def spa_catch_all(_=None):
    return FileResponse(INDEX_FILE)
