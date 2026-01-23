from typing import Optional, Any, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import Request

from app.models.audit_log import AuditLog
from app.models.user import User


class AuditService:
    """Сервис для журналирования действий пользователей."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log(
        self,
        action: str,
        user: Optional[User] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        entity_name: Optional[str] = None,
        description: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """
        Записать действие в журнал.
        
        Args:
            action: Тип действия (CREATE, UPDATE, DELETE, LOGIN, LOGOUT и т.д.)
            user: Пользователь, выполнивший действие
            entity_type: Тип сущности (event, layer, user, zone и т.д.)
            entity_id: ID сущности
            entity_name: Название сущности
            description: Описание действия
            details: Дополнительные данные в формате словаря
            request: FastAPI Request для получения IP и User-Agent
        
        Returns:
            Созданная запись журнала
        """
        # Получаем информацию из запроса
        ip_address = None
        user_agent = None
        
        if request:
            # Получаем IP (учитываем прокси)
            forwarded = request.headers.get("X-Forwarded-For")
            if forwarded:
                ip_address = forwarded.split(",")[0].strip()
            else:
                ip_address = request.client.host if request.client else None
            
            user_agent = request.headers.get("User-Agent", "")[:500]
        
        # Создаём запись
        audit_log = AuditLog(
            action=action,
            user_id=user.id if user else None,
            user_name=user.full_name if user else None,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            description=description,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        
        return audit_log
    
    def log_create(
        self,
        user: User,
        entity_type: str,
        entity_id: int,
        entity_name: str,
        description: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Shortcut для логирования создания."""
        return self.log(
            action="CREATE",
            user=user,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            description=description or f"Создан(а) {entity_type}: {entity_name}",
            details=details,
            request=request,
        )
    
    def log_update(
        self,
        user: User,
        entity_type: str,
        entity_id: int,
        entity_name: str,
        changes: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Shortcut для логирования обновления."""
        return self.log(
            action="UPDATE",
            user=user,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            description=description or f"Обновлён(а) {entity_type}: {entity_name}",
            details={"changes": changes} if changes else None,
            request=request,
        )
    
    def log_delete(
        self,
        user: User,
        entity_type: str,
        entity_id: int,
        entity_name: str,
        description: Optional[str] = None,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Shortcut для логирования удаления."""
        return self.log(
            action="DELETE",
            user=user,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            description=description or f"Удалён(а) {entity_type}: {entity_name}",
            request=request,
        )
    
    def log_login(
        self,
        user: User,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Логирование входа в систему."""
        return self.log(
            action="LOGIN",
            user=user,
            description=f"Вход в систему: {user.full_name}",
            request=request,
        )
    
    def log_logout(
        self,
        user: User,
        request: Optional[Request] = None,
    ) -> AuditLog:
        """Логирование выхода из системы."""
        return self.log(
            action="LOGOUT",
            user=user,
            description=f"Выход из системы: {user.full_name}",
            request=request,
        )
    
    def cleanup_old_records(self, days: int = 90) -> int:
        """
        Удалить записи журнала старше указанного количества дней.
        
        Args:
            days: Количество дней (по умолчанию 90)
        
        Returns:
            Количество удалённых записей
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted = self.db.query(AuditLog).filter(AuditLog.created_at < cutoff_date).delete()
        self.db.commit()
        return deleted


def cleanup_audit_logs(db: Session, days: int = 90) -> int:
    """Standalone функция для очистки старых записей журнала."""
    service = AuditService(db)
    return service.cleanup_old_records(days)
