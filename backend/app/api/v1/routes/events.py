from typing import List, Optional
from datetime import datetime
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session, joinedload

from app.core.security import get_current_user, require_roles
from app.db.session import get_db
from app.models.user import User
from app.models.event import Event
from app.models.event_image import EventImage
from app.models.event_document import EventDocument
from app.models.administrative_zone import AdministrativeZone
from app.schemas.event import EventOut, EventListOut, EventCreate


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
    """Получить список всех событий."""
    events = (
        db.query(Event)
        .options(
            joinedload(Event.administrative_zone),
            joinedload(Event.created_by),
            joinedload(Event.images),
            joinedload(Event.documents),
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
                created_by_id=ev.created_by_id,
                created_by_name=ev.created_by.full_name if ev.created_by else None,
                created_at=ev.created_at,
                images_count=len(ev.images) if ev.images else 0,
                documents_count=len(ev.documents) if ev.documents else 0,
            )
        )

    return result


@router.get("/{event_id}", response_model=EventOut)
def get_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить событие по ID."""
    event = (
        db.query(Event)
        .options(
            joinedload(Event.administrative_zone),
            joinedload(Event.created_by),
            joinedload(Event.images),
            joinedload(Event.documents),
        )
        .filter(Event.id == event_id)
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
        created_by_id=event.created_by_id,
        created_by_name=event.created_by.full_name if event.created_by else None,
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
    )


@router.post("/", response_model=EventOut, status_code=status.HTTP_201_CREATED)
async def create_event(
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
        created_by_id=current_user.id,
        created_by_name=current_user.full_name,
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


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: int,
    current_user: User = Depends(require_roles("admin", "editor", "editor_plus")),
    db: Session = Depends(get_db),
):
    """Удалить событие (для администраторов и редакторов)."""
    event = db.query(Event).filter(Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    
    # Удаляем файлы с диска
    for img in event.images or []:
        file_path = UPLOAD_DIR.parent / "backend" / img.file_path.lstrip("/")
        if file_path.exists():
            file_path.unlink()
    
    for doc in event.documents or []:
        file_path = UPLOAD_DIR.parent / "backend" / doc.file_path.lstrip("/")
        if file_path.exists():
            file_path.unlink()
    
    db.delete(event)
    db.commit()
