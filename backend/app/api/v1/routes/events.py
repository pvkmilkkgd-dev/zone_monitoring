from typing import List, Optional
from datetime import datetime
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, Request
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql import func

from app.core.security import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import User
from app.models.event import Event
from app.models.event_image import EventImage
from app.models.event_document import EventDocument
from app.models.event_comment import EventComment
from app.models.administrative_zone import AdministrativeZone
from app.schemas.event import EventOut, EventListOut, EventCreate, EventUpdate, EventCommentOut, EventCommentCreate
from app.services.audit_service import AuditService


router = APIRouter(prefix="/events", tags=["events"])

# Директория для загрузки файлов
UPLOAD_DIR = Path(__file__).resolve().parents[4] / "uploads"
IMAGES_DIR = UPLOAD_DIR / "images"
DOCUMENTS_DIR = UPLOAD_DIR / "documents"


def ensure_upload_dirs():
    """Создаёт директории для загрузки если они не существуют."""
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/", response_model=List[EventListOut])
def list_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить список всех событий (без удалённых)."""
    events = (
        db.query(Event)
        .filter(Event.is_deleted == False)
        .options(
            joinedload(Event.administrative_zone),
            joinedload(Event.created_by),
            joinedload(Event.updated_by),
            joinedload(Event.images),
            joinedload(Event.documents),
            joinedload(Event.comments.and_(EventComment.is_deleted == False)),
        )
        .order_by(Event.created_at.desc())
        .limit(100)
        .all()
    )

    result: List[EventListOut] = []
    for ev in events:
        result.append(
            EventListOut(
                id=ev.id,
                map_id=ev.map_id,
                administrative_zone_id=ev.administrative_zone_id,
                department_name=ev.administrative_zone.department_name if ev.administrative_zone else None,
                district_name=ev.district_name,
                status=ev.status,
                title=ev.title,
                description=ev.description,
                importance=ev.importance,
                is_archived=ev.is_archived or False,
                layer_id=ev.layer_id,
                sub_layer_id=ev.sub_layer_id,
                sub_sub_layer_id=ev.sub_sub_layer_id,
                created_by_id=ev.created_by_id,
                created_by_name=ev.created_by.full_name if ev.created_by else None,
                updated_by_id=ev.updated_by_id,
                updated_by_name=ev.updated_by.full_name if ev.updated_by else None,
                created_at=ev.created_at,
                updated_at=ev.updated_at,
                images_count=len(ev.images) if ev.images else 0,
                documents_count=len(ev.documents) if ev.documents else 0,
                comments_count=len(ev.comments) if ev.comments else 0,
            )
        )

    return result


@router.get("/{event_id}", response_model=EventOut)
def get_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить событие по ID (не удалённое)."""
    event = (
        db.query(Event)
        .filter(Event.id == event_id, Event.is_deleted == False)
        .options(
            joinedload(Event.administrative_zone),
            joinedload(Event.created_by),
            joinedload(Event.updated_by),
            joinedload(Event.images),
            joinedload(Event.documents),
            joinedload(Event.comments.and_(EventComment.is_deleted == False)).joinedload(EventComment.user),
        )
        .first()
    )
    
    if not event:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    
    return EventOut(
        id=event.id,
        map_id=event.map_id,
        administrative_zone_id=event.administrative_zone_id,
        department_name=event.administrative_zone.department_name if event.administrative_zone else None,
        district_name=event.district_name,
        status=event.status,
        title=event.title,
        description=event.description,
        importance=event.importance,
        is_archived=event.is_archived or False,
        layer_id=event.layer_id,
        sub_layer_id=event.sub_layer_id,
        sub_sub_layer_id=event.sub_sub_layer_id,
        created_by_id=event.created_by_id,
        created_by_name=event.created_by.full_name if event.created_by else None,
        updated_by_id=event.updated_by_id,
        updated_by_name=event.updated_by.full_name if event.updated_by else None,
        created_at=event.created_at,
        updated_at=event.updated_at,
        images=[
            {"id": img.id, "name": img.name, "file_path": img.file_path, "created_at": img.created_at}
            for img in (event.images or [])
        ],
        documents=[
            {"id": doc.id, "name": doc.name, "file_path": doc.file_path, "created_at": doc.created_at}
            for doc in (event.documents or [])
        ],
        comments=[
            EventCommentOut(
                id=c.id, event_id=c.event_id, user_id=c.user_id,
                user_name=c.user.full_name if c.user else None,
                text=c.text, created_at=c.created_at
            )
            for c in (event.comments or [])
        ],
    )


@router.post("/", response_model=EventOut, status_code=status.HTTP_201_CREATED)
async def create_event(
    request: Request,
    map_id: int = Form(...),
    district_name: str = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    importance: int = Form(5),
    layer_id: Optional[int] = Form(None),
    sub_layer_id: Optional[int] = Form(None),
    sub_sub_layer_id: Optional[int] = Form(None),
    images: List[UploadFile] = File(default=[]),
    documents: List[UploadFile] = File(default=[]),
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Создать новое событие (для администраторов и редакторов)."""
    ensure_upload_dirs()
    
    # Валидация importance
    if importance < 1 or importance > 10:
        raise HTTPException(status_code=400, detail="Коэффициент важности должен быть от 1 до 10")
    
    # Находим административную зону по названию района
    admin_zone = None
    all_zones = db.query(AdministrativeZone).all()
    for zone in all_zones:
        if district_name in (zone.district_names or []):
            admin_zone = zone
            break
    
    # Создаём событие
    event = Event(
        map_id=map_id,
        district_name=district_name,
        administrative_zone_id=admin_zone.id if admin_zone else None,
        created_by_id=current_user.id,
        title=title,
        description=description,
        importance=importance,
        status="warning",
        layer_id=layer_id,
        sub_layer_id=sub_layer_id,
        sub_sub_layer_id=sub_sub_layer_id,
    )
    db.add(event)
    db.flush()  # Получаем ID события
    
    # Сохраняем изображения
    saved_images = []
    for img_file in images:
        if img_file.filename:
            ext = Path(img_file.filename).suffix
            filename = f"{uuid.uuid4()}{ext}"
            file_path = IMAGES_DIR / filename
            
            content = await img_file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            event_image = EventImage(
                event_id=event.id,
                name=img_file.filename,
                file_path=f"/uploads/images/{filename}",
                created_at=datetime.utcnow(),
            )
            db.add(event_image)
            saved_images.append(event_image)
    
    # Сохраняем документы
    saved_documents = []
    for doc_file in documents:
        if doc_file.filename:
            ext = Path(doc_file.filename).suffix
            filename = f"{uuid.uuid4()}{ext}"
            file_path = DOCUMENTS_DIR / filename
            
            content = await doc_file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            event_document = EventDocument(
                event_id=event.id,
                name=doc_file.filename,
                file_path=f"/uploads/documents/{filename}",
                created_at=datetime.utcnow(),
            )
            db.add(event_document)
            saved_documents.append(event_document)
    
    db.commit()
    db.refresh(event)
    
    # Логируем создание события
    audit = AuditService(db)
    audit.log(
        action="CREATE",
        user=current_user,
        entity_type="event",
        entity_id=event.id,
        entity_name=event.title,
        description=f"Создано событие '{event.title}' в районе '{event.district_name}'",
        details={"importance": event.importance, "district_name": event.district_name},
        request=request,
    )
    
    return EventOut(
        id=event.id,
        map_id=event.map_id,
        administrative_zone_id=event.administrative_zone_id,
        department_name=admin_zone.department_name if admin_zone else None,
        district_name=event.district_name,
        status=event.status,
        title=event.title,
        description=event.description,
        importance=event.importance,
        layer_id=event.layer_id,
        sub_layer_id=event.sub_layer_id,
        sub_sub_layer_id=event.sub_sub_layer_id,
        created_by_id=current_user.id,
        created_by_name=current_user.full_name,
        updated_by_id=None,
        updated_by_name=None,
        created_at=event.created_at,
        updated_at=event.updated_at,
        images=[
            {"id": img.id, "name": img.name, "file_path": img.file_path, "created_at": img.created_at}
            for img in saved_images
        ],
        documents=[
            {"id": doc.id, "name": doc.name, "file_path": doc.file_path, "created_at": doc.created_at}
            for doc in saved_documents
        ],
    )


@router.put("/{event_id}", response_model=EventOut)
def update_event(
    request: Request,
    event_id: int,
    payload: EventUpdate,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Обновить событие (для администраторов и редакторов)."""
    event = (
        db.query(Event)
        .filter(Event.is_deleted == False)
        .options(
            joinedload(Event.administrative_zone),
            joinedload(Event.created_by),
            joinedload(Event.updated_by),
            joinedload(Event.images),
            joinedload(Event.documents),
        )
        .filter(Event.id == event_id)
        .first()
    )
    
    if not event:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    
    # Проверка прав: editor может редактировать только свои события
    if current_user.role == "editor" and event.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Вы можете редактировать только созданные вами события")
    
    old_title = event.title
    
    # Обновляем поля
    if payload.title is not None:
        event.title = payload.title
    if payload.description is not None:
        event.description = payload.description
    if payload.importance is not None:
        if payload.importance < 1 or payload.importance > 10:
            raise HTTPException(status_code=400, detail="Коэффициент важности должен быть от 1 до 10")
        event.importance = payload.importance
    if payload.status is not None:
        event.status = payload.status
    if payload.district_name is not None:
        event.district_name = payload.district_name
        # Пересчитываем административную зону
        admin_zone = None
        all_zones = db.query(AdministrativeZone).all()
        for zone in all_zones:
            if payload.district_name in (zone.district_names or []):
                admin_zone = zone
                break
        event.administrative_zone_id = admin_zone.id if admin_zone else None
    
    # Обновляем слои
    if payload.layer_id is not None:
        event.layer_id = payload.layer_id if payload.layer_id != 0 else None
    if payload.sub_layer_id is not None:
        event.sub_layer_id = payload.sub_layer_id if payload.sub_layer_id != 0 else None
    if payload.sub_sub_layer_id is not None:
        event.sub_sub_layer_id = payload.sub_sub_layer_id if payload.sub_sub_layer_id != 0 else None
    
    # Обновляем is_archived
    if payload.is_archived is not None:
        event.is_archived = payload.is_archived
    
    # Устанавливаем кто обновил (updated_at обновится автоматически через onupdate)
    event.updated_by_id = current_user.id
    event.updated_at = func.now()
    
    db.commit()
    
    # Логируем
    AuditService(db).log(
        action="UPDATE",
        user=current_user,
        entity_type="event",
        entity_id=event_id,
        entity_name=event.title,
        description=f"Обновлено событие '{old_title}'",
        details={"payload": payload.model_dump(exclude_unset=True)},
        request=request,
    )
    
    # Перезагружаем событие со всеми связями
    event = (
        db.query(Event)
        .options(
            joinedload(Event.administrative_zone),
            joinedload(Event.created_by),
            joinedload(Event.updated_by),
            joinedload(Event.images),
            joinedload(Event.documents),
            joinedload(Event.comments).joinedload(EventComment.user),
        )
        .filter(Event.id == event_id)
        .first()
    )
    
    return EventOut(
        id=event.id,
        map_id=event.map_id,
        administrative_zone_id=event.administrative_zone_id,
        department_name=event.administrative_zone.department_name if event.administrative_zone else None,
        district_name=event.district_name,
        status=event.status,
        title=event.title,
        description=event.description,
        importance=event.importance,
        is_archived=event.is_archived or False,
        layer_id=event.layer_id,
        sub_layer_id=event.sub_layer_id,
        sub_sub_layer_id=event.sub_sub_layer_id,
        created_by_id=event.created_by_id,
        created_by_name=event.created_by.full_name if event.created_by else None,
        updated_by_id=event.updated_by_id,
        updated_by_name=event.updated_by.full_name if event.updated_by else None,
        created_at=event.created_at,
        updated_at=event.updated_at,
        images=[
            {"id": img.id, "name": img.name, "file_path": img.file_path, "created_at": img.created_at}
            for img in (event.images or [])
        ],
        documents=[
            {"id": doc.id, "name": doc.name, "file_path": doc.file_path, "created_at": doc.created_at}
            for doc in (event.documents or [])
        ],
        comments=[
            EventCommentOut(
                id=c.id, event_id=c.event_id, user_id=c.user_id,
                user_name=c.user.full_name if c.user else None,
                text=c.text, created_at=c.created_at
            )
            for c in (event.comments or [])
        ],
    )


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    request: Request,
    event_id: int,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Мягкое удаление события (для администраторов и редакторов)."""
    event = db.query(Event).filter(Event.id == event_id, Event.is_deleted == False).first()
    if not event:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    
    # Проверка прав: editor может удалять только свои события
    if current_user.role == "editor" and event.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Вы можете удалять только созданные вами события")
    
    event_title = event.title
    
    # Мягкое удаление - файлы оставляем на диске
    event.is_deleted = True
    db.commit()
    
    # Логируем удаление
    audit = AuditService(db)
    audit.log(
        action="DELETE",
        user=current_user,
        entity_type="event",
        entity_id=event_id,
        entity_name=event_title,
        description=f"Удалено событие '{event_title}'",
        request=request,
    )


@router.post("/{event_id}/comments", response_model=EventCommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(
    request: Request,
    event_id: int,
    payload: EventCommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Добавить комментарий к событию."""
    event = db.query(Event).filter(Event.id == event_id, Event.is_deleted == False).first()
    if not event:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    
    comment = EventComment(
        event_id=event_id,
        user_id=current_user.id,
        text=payload.text,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    # Логируем
    AuditService(db).log(
        action="CREATE",
        user=current_user,
        entity_type="comment",
        entity_id=comment.id,
        entity_name=f"Комментарий к событию '{event.title}'",
        description=f"Добавлен комментарий к событию '{event.title}'",
        details={"event_id": event_id, "text": payload.text[:100]},
        request=request,
    )
    
    return EventCommentOut(
        id=comment.id,
        event_id=comment.event_id,
        user_id=comment.user_id,
        user_name=current_user.full_name,
        text=comment.text,
        created_at=comment.created_at,
    )


@router.delete("/{event_id}/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    request: Request,
    event_id: int,
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Мягкое удаление комментария к событию."""
    comment = db.query(EventComment).filter(
        EventComment.id == comment_id,
        EventComment.event_id == event_id,
        EventComment.is_deleted == False
    ).first()
    
    if not comment:
        raise HTTPException(status_code=404, detail="Комментарий не найден")
    
    # Мягкое удаление
    comment.is_deleted = True
    db.commit()
    
    # Логируем
    AuditService(db).log(
        action="DELETE",
        user=current_user,
        entity_type="comment",
        entity_id=comment_id,
        entity_name=f"Комментарий ID:{comment_id}",
        description=f"Удалён комментарий к событию (event_id={event_id})",
        details={"event_id": event_id},
        request=request,
    )
    
    return None
