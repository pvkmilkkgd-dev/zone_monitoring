from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.admin_settings import router as admin_settings_router
from app.api.v1.routes.auth import router as auth_router
from app.core.bootstrap import require_bootstrap_completed


app = FastAPI(
    title="Debug App",
    version="0.1.0",
)

# CORS — по желанию, можно убрать
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


# 🔹 Подключаем роутеры
app.include_router(auth_router, prefix="/api/v1")
app.include_router(
    admin_settings_router,
    prefix="/api/v1",
    dependencies=[Depends(require_bootstrap_completed)],
)
