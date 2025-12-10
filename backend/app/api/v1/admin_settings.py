from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
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
    _: None = Depends(get_current_admin),
):
    """Получить текущие настройки системы (может быть None, если ещё не сохранены)."""
    settings = db.query(SystemSettings).order_by(SystemSettings.id.asc()).first()
    return settings


@router.put("/", response_model=SystemSettingsResponse)
def update_system_settings(
    payload: SystemSettingsUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(get_current_admin),
):
    """
    Создать или обновить настройки системы.
    """
    settings = db.query(SystemSettings).order_by(SystemSettings.id.asc()).first()

    if settings is None:
        settings = SystemSettings(
            region=payload.region,
            department_name=payload.department_name,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
        return settings

    settings.region = payload.region
    settings.department_name = payload.department_name

    db.commit()
    db.refresh(settings)
    return settings
