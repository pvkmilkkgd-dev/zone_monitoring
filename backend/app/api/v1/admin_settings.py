import logging

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin_user
from app.core.security import get_current_user
from app.db.session import get_db
from app.models.map import Map
from app.models.system_settings import SystemSettings
from app.models.user import User
from app.schemas.settings import SystemSettingsResponse, SystemSettingsUpdate

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/settings",
    tags=["admin"],
)


@router.get("/", response_model=SystemSettingsResponse | None)
def get_system_settings(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),  # Доступно всем авторизованным пользователям
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
        db.flush()  # чтобы получить текущие значения

    data = payload.model_dump(exclude_unset=True)

    # --- Soft-delete данных удалённых регионов ---
    if "region_ids" in data and data["region_ids"] is not None:
        old_region_ids = list(settings.region_ids or [])
        new_region_ids = data["region_ids"]
        removed_ids = set(str(r) for r in old_region_ids) - set(str(r) for r in new_region_ids)

        logger.info(
            "Region change: old=%s, new=%s, removed=%s, deactivate=%s",
            [str(r) for r in old_region_ids],
            [str(r) for r in new_region_ids],
            removed_ids,
            payload.deactivate_removed,
        )

        if removed_ids and payload.deactivate_removed:
            # Получаем имена районов ОСТАВШИХСЯ регионов (то, что надо сохранить)
            kept_ids = [str(r) for r in new_region_ids]
            if kept_ids:
                kept_rows = db.execute(
                    text("SELECT name FROM districts WHERE region_id::text = ANY(:ids)"),
                    {"ids": kept_ids},
                ).fetchall()
                kept_district_names = [row[0] for row in kept_rows]
            else:
                kept_district_names = []

            logger.info(
                "Kept district names: %d (from %d regions)",
                len(kept_district_names),
                len(kept_ids),
            )

            # Soft-delete событий, чей district_name НЕ принадлежит оставшимся регионам
            if kept_district_names:
                ev_result = db.execute(
                    text(
                        "UPDATE events SET is_deleted = TRUE "
                        "WHERE is_deleted = FALSE "
                        "AND (district_name IS NULL OR district_name != ALL(:names))"
                    ),
                    {"names": kept_district_names},
                )
            else:
                # Нет оставшихся регионов — деактивируем все активные события
                ev_result = db.execute(
                    text(
                        "UPDATE events SET is_deleted = TRUE "
                        "WHERE is_deleted = FALSE"
                    ),
                )
            logger.info("Events soft-deleted: %d rows", ev_result.rowcount)

            # Soft-delete административных зон, у которых НЕ ВСЕ district_names
            # принадлежат оставшимся регионам
            kept_set = set(kept_district_names)
            all_zones = db.execute(
                text(
                    "SELECT id, district_names FROM administrative_zones "
                    "WHERE is_deleted = FALSE"
                )
            ).fetchall()
            zones_to_deactivate = []
            for zone_id, zone_districts in all_zones:
                names_list = zone_districts if isinstance(zone_districts, list) else []
                if not names_list:
                    # Зона без районов — деактивируем
                    zones_to_deactivate.append(zone_id)
                elif not all(n in kept_set for n in names_list):
                    # Хотя бы один район не в оставшихся — деактивируем
                    zones_to_deactivate.append(zone_id)

            if zones_to_deactivate:
                db.execute(
                    text(
                        "UPDATE administrative_zones SET is_deleted = TRUE "
                        "WHERE id = ANY(:ids)"
                    ),
                    {"ids": zones_to_deactivate},
                )
            logger.info("Zones soft-deleted: %d", len(zones_to_deactivate))

    # --- Обновление полей настроек ---
    if "department_name" in data:
        settings.department_name = data["department_name"]

    if "region_ids" in data and data["region_ids"] is not None:
        settings.region_ids = data["region_ids"]
        settings.region = payload.region
    elif "region" in data and data["region"] is not None:
        settings.region = data["region"]

    # Автоматически создаём или обновляем карту с id=1
    # Это необходимо для работы административных зон
    default_map = db.query(Map).filter(Map.id == 1).first()
    map_name = settings.region or "Основная карта"
    
    if default_map:
        # Обновляем существующую карту
        default_map.name = map_name
        default_map.description = "Карта региона для административных зон"
    else:
        # Создаём новую карту
        default_map = Map(
            id=1,
            name=map_name,
            description="Карта региона для административных зон",
        )
        db.add(default_map)

    db.commit()
    db.refresh(settings)
    return settings
