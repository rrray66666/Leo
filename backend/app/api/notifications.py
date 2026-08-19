from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user, get_db
from app.models.notification import Notification
from app.models.user import User
from app.services.notification_service import (
    get_unread_count,
    mark_all_as_read,
)

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])

# Frontend filter categories -> actual Notification.type values stored in DB
TYPE_CATEGORY_MAP = {
    "system": ["system", "auto_lost", "task_due", "payment_overdue"],
    "stage_change": ["stage_change", "stage_alert"],
    "alert": ["alert", "stage_alert"],
    "follow_up": ["follow_up"],
}


def _serialize_notification(n) -> dict:
    """Convert ORM Notification object to plain dict for JSON response"""
    return {
        "id": str(n.id),
        "user_id": str(n.user_id),
        "type": n.type,
        "title": n.title,
        "content": n.content,
        "related_id": str(n.related_id) if n.related_id else None,
        "related_type": n.related_type,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "updated_at": n.updated_at.isoformat() if n.updated_at else None,
    }


@router.get("", response_model=dict)
def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Notification list (paginated, optionally filtered by type category)"""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)

    if type:
        if type in TYPE_CATEGORY_MAP:
            query = query.filter(Notification.type.in_(TYPE_CATEGORY_MAP[type]))
        else:
            query = query.filter(Notification.type == type)

    total = query.count()
    notifications = (
        query.order_by(Notification.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": [_serialize_notification(x) for x in notifications],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get("/unread-count", response_model=dict)
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Unread notification count"""
    count = get_unread_count(db, current_user.id)
    return {"code": 0, "message": "success", "data": {"count": count}}


@router.put("/{id}/read", response_model=dict)
def mark_read(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark as read"""
    notification = (
        db.query(Notification)
        .filter(Notification.id == id, Notification.user_id == current_user.id)
        .first()
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return {"code": 0, "message": "success", "data": _serialize_notification(notification)}


@router.put("/read-all", response_model=dict)
def read_all(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark all as read"""
    count = mark_all_as_read(db, current_user.id)
    return {"code": 0, "message": "success", "data": {"affected": count}}
