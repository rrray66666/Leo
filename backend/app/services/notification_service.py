from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.notification import Notification


def create_notification(
    db: Session,
    user_id: UUID,
    type: str,
    title: str,
    content: Optional[str] = None,
    related_id: Optional[UUID] = None,
    related_type: Optional[str] = None,
) -> Notification:
    """Create a notification"""
    notification = Notification(
        user_id=user_id,
        type=type,
        title=title,
        content=content,
        related_id=related_id,
        related_type=related_type,
        is_read=False,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def get_unread_count(db: Session, user_id: UUID) -> int:
    """Get unread notification count for user"""
    return (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.is_read == False,
        )
        .count()
    )


def mark_as_read(db: Session, notification_id: UUID) -> Optional[Notification]:
    """Mark notification as read"""
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id)
        .first()
    )
    if notification:
        notification.is_read = True
        db.commit()
        db.refresh(notification)
    return notification


def mark_all_as_read(db: Session, user_id: UUID) -> int:
    """Mark all notifications as read for user"""
    count = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id,
            Notification.is_read == False,
        )
        .update({"is_read": True}, synchronize_session=False)
    )
    db.commit()
    return count
