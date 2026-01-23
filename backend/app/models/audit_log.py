from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


class AuditLog(Base):
    """Модель для хранения журнала действий пользователей."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Действие
    action = Column(String(50), nullable=False, index=True, comment="Тип действия: CREATE, UPDATE, DELETE, LOGIN, LOGOUT и т.д.")
    
    # Пользователь
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_name = Column(String(255), nullable=True, comment="Имя пользователя на момент действия")
    
    # Сущность
    entity_type = Column(String(100), nullable=True, index=True, comment="Тип сущности: event, layer, user, zone и т.д.")
    entity_id = Column(Integer, nullable=True, comment="ID сущности")
    entity_name = Column(String(500), nullable=True, comment="Название сущности на момент действия")
    
    # Описание
    description = Column(Text, nullable=True, comment="Описание действия")
    
    # Дополнительные данные
    details = Column(JSON, nullable=True, comment="JSON с дополнительными данными")
    
    # Информация о запросе
    ip_address = Column(String(45), nullable=True, comment="IP адрес")
    user_agent = Column(String(500), nullable=True, comment="User-Agent браузера")
    
    # Время
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)
    
    # Связи
    user = relationship("User", backref="audit_logs")
