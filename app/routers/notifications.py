from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import User, require_roles
from app.database import get_db
from app.models import NotificationEvent
from app.schemas import NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clerk")),
    unread_only: bool = Query(default=False),
    event_type: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
):
    query = db.query(NotificationEvent)
    if unread_only:
        query = query.filter(NotificationEvent.is_read == 0)
    if event_type is not None:
        query = query.filter(NotificationEvent.event_type == event_type)
    if date_from is not None:
        query = query.filter(NotificationEvent.created_at >= date_from)
    if date_to is not None:
        query = query.filter(NotificationEvent.created_at <= date_to)
    return query.order_by(NotificationEvent.id.desc()).all()


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "clerk")),
):
    notification = db.query(NotificationEvent).filter(NotificationEvent.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = 1
    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification
