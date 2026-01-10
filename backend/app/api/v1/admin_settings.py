from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.core.db import get_db
from app.models.system_settings import SystemSettings
from app.schemas.settings import SystemSettingsResponse, SystemSettingsUpdate

router = APIRouter(
    prefix="/admin/settings",
    tags=["admin"],
)


@router.get("/", response_model=SystemSettingsResponse | None)
def get_system_settings(
    db: Session = Depends(get_db),
    _: None = Depends(get_current_admin_user),
):
    """Получить текущие настройки системы (может быть None, если ещё не сохранены)."""
    settings = db.query(SystemSettings).order_by(SystemSettings.id.asc()).first()
    return settings


@router.put("/", response_model=SystemSettingsResponse)
def update_system_settings(
    payload: SystemSettingsUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(get_current_admin_user),
):
    settings = db.query(SystemSettings).order_by(SystemSettings.id.asc()).first()

    if settings is None:
        settings = SystemSettings()
        db.add(settings)

    settings.department_name = payload.department_name

    if payload.region_ids is not None:
        settings.region_ids = payload.region_ids
        # оставляем поддержку старого поля region для совместимости
        settings.region = payload.region
    else:
        # если фронт шлёт старое поле region строкой — не трогаем region_ids
        if payload.region is not None:
            settings.region = payload.region

    db.commit()
    db.refresh(settings)
    return settings
