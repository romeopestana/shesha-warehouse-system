from app.models import NotificationEvent


def emit_notification(
    *,
    db,
    event_type: str,
    message: str,
    related_id: int | None = None,
) -> NotificationEvent:
    event = NotificationEvent(
        event_type=event_type,
        message=message,
        related_id=related_id,
        is_read=0,
    )
    db.add(event)
    return event
