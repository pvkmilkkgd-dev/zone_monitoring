from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes import auth as auth_routes, events as events_routes
from app.api.v1.routes import maps, zones, zone_state, users

app = FastAPI(title="Zone Monitoring API", version="0.1.0")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_prefix = "/api/v1"
app.include_router(auth_routes.router, prefix="/api/v1/auth")
app.include_router(events_routes.router, prefix="/api/v1")
app.include_router(zones.router, prefix=api_prefix, tags=["zones"])
app.include_router(zone_state.router, prefix=api_prefix, tags=["zone_state"])
app.include_router(maps.router, prefix=api_prefix, tags=["maps"])
app.include_router(users.router, prefix=api_prefix, tags=["users"])


@app.get("/health")
def health():
    return {"status": "ok"}
