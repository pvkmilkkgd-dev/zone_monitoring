from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes import auth as auth_routes
from app.api.v1.routes import maps, zones, zone_state, users
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="Zone Monitoring API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api_prefix = "/api/v1"
    app.include_router(auth_routes.router, prefix=api_prefix, tags=["auth"])
    app.include_router(zones.router, prefix=api_prefix, tags=["zones"])
    app.include_router(zone_state.router, prefix=api_prefix, tags=["zone_state"])
    app.include_router(maps.router, prefix=api_prefix, tags=["maps"])
    app.include_router(users.router, prefix=api_prefix, tags=["users"])

    return app


app = create_app()

