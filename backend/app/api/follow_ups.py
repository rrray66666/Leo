from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import (
    check_customer_access,
    get_current_active_user,
    get_db,
)
from app.models.customer import Customer
from app.models.follow_up import FollowUp
from app.models.user import User

router = APIRouter(prefix="/api/v1", tags=["Follow-up Reminders"])

# Valid remind_type values (must match the frontend option list)
VALID_REMIND_TYPES = ("system_notification", "email", "high_priority")


def _serialize_follow_up(f: FollowUp) -> dict:
    """Convert ORM FollowUp object to plain dict for JSON response"""
    return {
        "id": str(f.id),
        "customer_id": str(f.customer_id),
        "user_id": str(f.user_id) if f.user_id else None,
        "title": f.title,
        "content": f.content,
        "remind_at": f.remind_at.isoformat() if f.remind_at else None,
        "remind_type": f.remind_type,
        "is_done": f.is_done,
        "done_at": f.done_at.isoformat() if f.done_at else None,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


def _validate_remind_type(remind_type: str) -> str:
    """Normalize/invalid remind_type to avoid MySQL Enum DataError"""
    if remind_type in VALID_REMIND_TYPES:
        return remind_type
    # Fallback for unknown values: keep the value only if backend supports it,
    # otherwise default to system_notification instead of crashing with 500.
    return "system_notification"


@router.post("/customers/{customer_id}/follow-ups", response_model=dict)
def create_follow_up(
    customer_id: UUID,
    title: str,
    content: str = None,
    remind_at: datetime = None,
    remind_type: str = "system_notification",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create follow-up reminder"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    check_customer_access(customer, current_user)

    remind_type = _validate_remind_type(remind_type)
    follow_up = FollowUp(
        customer_id=customer_id,
        user_id=current_user.id,
        title=title,
        content=content,
        remind_at=remind_at,
        remind_type=remind_type,
        is_done=False,
    )
    db.add(follow_up)
    db.commit()
    db.refresh(follow_up)
    return {"code": 0, "message": "success", "data": _serialize_follow_up(follow_up)}


@router.get("/customers/{customer_id}/follow-ups", response_model=dict)
def list_follow_ups(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List customer follow-up reminders"""
    from app.core.deps import check_customer_access
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    check_customer_access(customer, current_user)
    follow_ups = (
        db.query(FollowUp)
        .filter(FollowUp.customer_id == customer_id)
        .order_by(FollowUp.created_at.desc())
        .all()
    )
    return {"code": 0, "message": "success", "data": [_serialize_follow_up(x) for x in follow_ups]}


@router.put("/follow-ups/{id}", response_model=dict)
def update_follow_up(
    id: UUID,
    title: str = None,
    content: str = None,
    remind_at: datetime = None,
    remind_type: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update follow-up reminder"""
    follow_up = db.query(FollowUp).filter(FollowUp.id == id).first()
    if not follow_up:
        raise HTTPException(status_code=404, detail="Follow-up reminder not found")
    customer = db.query(Customer).filter(Customer.id == follow_up.customer_id).first()
    check_customer_access(customer, current_user)

    if title is not None:
        follow_up.title = title
    if content is not None:
        follow_up.content = content
    if remind_at is not None:
        follow_up.remind_at = remind_at
    if remind_type is not None:
        follow_up.remind_type = _validate_remind_type(remind_type)

    db.commit()
    db.refresh(follow_up)
    return {"code": 0, "message": "success", "data": _serialize_follow_up(follow_up)}


@router.put("/follow-ups/{id}/done", response_model=dict)
def mark_follow_up_done(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Mark follow-up as done"""
    follow_up = db.query(FollowUp).filter(FollowUp.id == id).first()
    if not follow_up:
        raise HTTPException(status_code=404, detail="Follow-up reminder not found")
    customer = db.query(Customer).filter(Customer.id == follow_up.customer_id).first()
    check_customer_access(customer, current_user)
    follow_up.is_done = True
    follow_up.done_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(follow_up)
    return {"code": 0, "message": "success", "data": _serialize_follow_up(follow_up)}


@router.delete("/follow-ups/{id}", response_model=dict)
def delete_follow_up(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete follow-up reminder"""
    follow_up = db.query(FollowUp).filter(FollowUp.id == id).first()
    if not follow_up:
        raise HTTPException(status_code=404, detail="Follow-up reminder not found")
    customer = db.query(Customer).filter(Customer.id == follow_up.customer_id).first()
    check_customer_access(customer, current_user)
    db.delete(follow_up)
    db.commit()
    return {"code": 0, "message": "success", "data": None}


@router.get("/follow-ups/today", response_model=dict)
def today_follow_ups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get today's follow-up reminders"""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    follow_ups = (
        db.query(FollowUp)
        .filter(
            FollowUp.user_id == current_user.id,
            FollowUp.is_done == False,
            FollowUp.remind_at >= today_start,
        )
        .order_by(FollowUp.remind_at.asc())
        .all()
    )
    return {"code": 0, "message": "success", "data": [_serialize_follow_up(x) for x in follow_ups]}
