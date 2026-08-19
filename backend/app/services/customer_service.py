from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.communication import Communication
from app.models.customer import Customer
from app.models.stage_history import StageHistory
from app.models.user import User
from app.services.audit_service import log_action
from app.services.stage_service import get_alert_level, get_stay_days


def create_customer(
    db: Session,
    data: dict,
    operator_id: Optional[UUID] = None,
) -> Customer:
    """Create customer"""
    # Check phone number uniqueness
    existing = db.query(Customer).filter(Customer.phone == data["phone"]).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Phone number already exists",
        )

    customer = Customer(**data)
    customer.current_stage = 1
    customer.stage_entered_at = datetime.now(timezone.utc)
    customer.status = "active"
    db.add(customer)
    db.commit()
    db.refresh(customer)
    log_action(
        db,
        operator_id,
        "create",
        "customer",
        object_id=customer.id,
        customer_id=customer.id,
        after_data={k: getattr(customer, k) for k in ("name", "phone", "company", "region") if hasattr(customer, k)},
    )
    return customer


def update_customer(
    db: Session,
    customer_id: UUID,
    data: dict,
    operator_id: Optional[UUID] = None,
) -> Customer:
    """Update customer info"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    # If updating phone, check uniqueness
    if "phone" in data and data["phone"] != customer.phone:
        existing = (
            db.query(Customer)
            .filter(Customer.phone == data["phone"], Customer.id != customer_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already in use by another customer",
            )

    before_data = {k: getattr(customer, k) for k in ("name", "phone", "company", "region", "contact_person", "wechat", "email", "source_channel")}
    for key, value in data.items():
        if value is not None:
            setattr(customer, key, value)

    customer.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(customer)
    after_data = {k: getattr(customer, k) for k in ("name", "phone", "company", "region", "contact_person", "wechat", "email", "source_channel")}
    log_action(
        db,
        operator_id,
        "update",
        "customer",
        object_id=customer.id,
        customer_id=customer.id,
        before_data=before_data,
        after_data=after_data,
    )
    return customer


def get_customer_detail(
    db: Session,
    customer_id: UUID,
) -> Customer:
    """Get customer detail (with related data)"""
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id)
        .first()
    )
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )
    return customer


def search_customers(
    db: Session,
    keyword: str,
    page: int = 1,
    page_size: int = 20,
    stage: Optional[int] = None,
    status_filter: Optional[str] = None,
    sales_id: Optional[UUID] = None,
    region: Optional[str] = None,
    alert_level: Optional[str] = None,
) -> tuple[list[Customer], int]:
    """Search customers"""
    query = db.query(Customer)

    # Soft-deleted customers are hidden from the list by default
    if status_filter != "deleted":
        query = query.filter(Customer.status != "deleted")

    # Keyword search
    if keyword:
        query = query.filter(
            or_(
                Customer.name.ilike(f"%{keyword}%"),
                Customer.contact_person.ilike(f"%{keyword}%"),
                Customer.phone.ilike(f"%{keyword}%"),
                Customer.wechat.ilike(f"%{keyword}%"),
                Customer.company.ilike(f"%{keyword}%"),
                Customer.email.ilike(f"%{keyword}%"),
            )
        )

    if stage is not None:
        query = query.filter(Customer.current_stage == stage)

    if status_filter:
        query = query.filter(Customer.status == status_filter)

    if sales_id:
        query = query.filter(Customer.sales_id == sales_id)

    if region:
        query = query.filter(Customer.region == region)

    # Alert level is computed from stage stay days (not a SQL column), so when
    # filtering by it we must filter the full result set in Python and paginate
    # manually - otherwise both the page content and the total would be wrong.
    if alert_level and alert_level != "all":
        all_customers = query.order_by(Customer.updated_at.desc()).all()
        filtered = [c for c in all_customers if get_alert_level(c) == alert_level]
        total = len(filtered)
        customers = filtered[(page - 1) * page_size : page * page_size]
    else:
        total = query.count()
        customers = (
            query.order_by(Customer.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

    return customers, total


def batch_assign(
    db: Session,
    customer_ids: list[UUID],
    new_sales_id: UUID,
) -> int:
    """Batch transfer sales person"""
    # Verify new sales person exists
    sales = db.query(User).filter(User.id == new_sales_id, User.role.in_(["sales", "admin"])).first()
    if not sales:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New sales person not found or incorrect role",
        )

    count = (
        db.query(Customer)
        .filter(Customer.id.in_(customer_ids))
        .update(
            {"sales_id": new_sales_id, "updated_at": datetime.now(timezone.utc)},
            synchronize_session=False,
        )
    )
    db.commit()
    return count


def batch_status(
    db: Session,
    customer_ids: list[UUID],
    status: str,
) -> int:
    """Batch update status"""
    count = (
        db.query(Customer)
        .filter(Customer.id.in_(customer_ids))
        .update(
            {"status": status, "updated_at": datetime.now(timezone.utc)},
            synchronize_session=False,
        )
    )
    db.commit()
    return count


def get_timeline(
    db: Session,
    customer_id: UUID,
) -> list[dict]:
    """Get customer timeline (stage history + communications + audit logs)"""
    timeline = []

    # Stage history
    histories = (
        db.query(StageHistory)
        .filter(StageHistory.customer_id == customer_id)
        .order_by(StageHistory.changed_at.desc())
        .all()
    )
    for h in histories:
        timeline.append({
            "type": "stage_change",
            "id": str(h.id),
            "time": h.changed_at,
            "data": {
                "from_stage": h.from_stage,
                "to_stage": h.to_stage,
                "remark": h.remark,
                "operator_id": str(h.changed_by) if h.changed_by else None,
            },
        })

    # Communications
    communications = (
        db.query(Communication)
        .filter(Communication.customer_id == customer_id)
        .order_by(Communication.created_at.desc())
        .all()
    )
    for c in communications:
        timeline.append({
            "type": "communication",
            "id": str(c.id),
            "time": c.created_at,
            "data": {
                "channel": c.channel,
                "content": c.content,
                "user_id": str(c.user_id) if c.user_id else None,
            },
        })

    # Audit logs
    audit_logs = (
        db.query(AuditLog)
        .filter(AuditLog.customer_id == customer_id)
        .order_by(AuditLog.created_at.desc())
        .all()
    )
    for a in audit_logs:
        timeline.append({
            "type": "audit_log",
            "id": str(a.id),
            "time": a.created_at,
            "data": {
                "action": a.action,
                "object_type": a.object_type,
                "user_id": str(a.user_id) if a.user_id else None,
            },
        })

    # Sort by time
    timeline.sort(key=lambda x: x["time"] or datetime.min, reverse=True)
    return timeline
