from typing import List, Optional
from datetime import datetime, date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.security import require_roles
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogOut


router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/", response_model=List[AuditLogOut])
def list_audit_logs(
    current_user=Depends(require_roles("admin")),
    db: Session = Depends(get_db),
    date_from: Optional[date] = Query(None, description="Дата начала периода"),
    date_to: Optional[date] = Query(None, description="Дата окончания периода"),
    action: Optional[str] = Query(None, description="Фильтр по типу действия"),
    entity_type: Optional[str] = Query(None, description="Фильтр по типу сущности"),
    user_id: Optional[int] = Query(None, description="Фильтр по пользователю"),
    search: Optional[str] = Query(None, description="Поиск по описанию"),
    limit: int = Query(100, ge=1, le=1000, description="Максимальное количество записей"),
    offset: int = Query(0, ge=0, description="Смещение"),
):
    """Получить журнал аудита (только для администраторов)."""
    query = db.query(AuditLog)
    
    # Фильтры
    if date_from:
        query = query.filter(AuditLog.created_at >= datetime.combine(date_from, datetime.min.time()))
    
    if date_to:
        query = query.filter(AuditLog.created_at <= datetime.combine(date_to, datetime.max.time()))
    
    if action:
        query = query.filter(AuditLog.action == action)
    
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    if search:
        query = query.filter(AuditLog.description.ilike(f"%{search}%"))
    
    # Сортировка по дате (новые сверху)
    query = query.order_by(desc(AuditLog.created_at))
    
    # Пагинация
    logs = query.offset(offset).limit(limit).all()
    
    return logs


@router.get("/export")
def export_audit_logs(
    current_user=Depends(require_roles("admin")),
    db: Session = Depends(get_db),
    date_from: Optional[date] = Query(None, description="Дата начала периода"),
    date_to: Optional[date] = Query(None, description="Дата окончания периода"),
    action: Optional[str] = Query(None, description="Фильтр по типу действия"),
    entity_type: Optional[str] = Query(None, description="Фильтр по типу сущности"),
    user_id: Optional[int] = Query(None, description="Фильтр по пользователю"),
):
    """Экспортировать журнал аудита в текстовый файл (только для администраторов)."""
    query = db.query(AuditLog)
    
    # Фильтры
    if date_from:
        query = query.filter(AuditLog.created_at >= datetime.combine(date_from, datetime.min.time()))
    
    if date_to:
        query = query.filter(AuditLog.created_at <= datetime.combine(date_to, datetime.max.time()))
    
    if action:
        query = query.filter(AuditLog.action == action)
    
    if entity_type:
        query = query.filter(AuditLog.entity_type == entity_type)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    # Сортировка по дате (старые сверху для логичного чтения)
    query = query.order_by(AuditLog.created_at)
    
    logs = query.all()
    
    # Формируем текстовый файл
    lines = []
    lines.append("=" * 80)
    lines.append("ЖУРНАЛ ОПЕРАЦИЙ")
    lines.append(f"Дата экспорта: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    if date_from:
        lines.append(f"Период с: {date_from.strftime('%d.%m.%Y')}")
    if date_to:
        lines.append(f"Период по: {date_to.strftime('%d.%m.%Y')}")
    lines.append(f"Всего записей: {len(logs)}")
    lines.append("=" * 80)
    lines.append("")
    
    for log in logs:
        lines.append("-" * 80)
        lines.append(f"[{log.created_at.strftime('%d.%m.%Y %H:%M:%S')}] {log.action}")
        lines.append(f"Пользователь: {log.user_name or 'Система'}")
        
        if log.entity_type:
            entity_info = f"Сущность: {log.entity_type}"
            if log.entity_id:
                entity_info += f" (ID: {log.entity_id})"
            if log.entity_name:
                entity_info += f" - {log.entity_name}"
            lines.append(entity_info)
        
        if log.description:
            lines.append(f"Описание: {log.description}")
        
        if log.ip_address:
            lines.append(f"IP: {log.ip_address}")
        
        if log.details:
            lines.append(f"Детали: {log.details}")
        
        lines.append("")
    
    lines.append("=" * 80)
    lines.append("Конец журнала")
    lines.append("=" * 80)
    
    content = "\n".join(lines)
    
    # Формируем имя файла
    filename_parts = ["journal"]
    if date_from:
        filename_parts.append(date_from.strftime("%Y%m%d"))
    if date_to:
        filename_parts.append(date_to.strftime("%Y%m%d"))
    filename = "_".join(filename_parts) + ".txt"
    
    return Response(
        content=content,
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        }
    )


@router.get("/actions")
def get_audit_actions(
    current_user=Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Получить список уникальных типов действий."""
    actions = db.query(AuditLog.action).distinct().all()
    return [a[0] for a in actions if a[0]]


@router.get("/entity-types")
def get_audit_entity_types(
    current_user=Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """Получить список уникальных типов сущностей."""
    types = db.query(AuditLog.entity_type).distinct().all()
    return [t[0] for t in types if t[0]]
