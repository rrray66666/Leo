from typing import Optional
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.services.stage_service import get_alert_level, get_stay_days


def get_kanban_data(
    db: Session,
    user_id: Optional[UUID] = None,
    filters: Optional[dict] = None,
) -> list[dict]:
    """Get kanban data - grouped by stage"""
    query = db.query(Customer).filter(Customer.status == "active")

    # sales/cs only see their own customers on the board
    if user_id is not None:
        query = query.filter(Customer.sales_id == user_id)

    if filters:
        if filters.get("sales_id"):
            query = query.filter(Customer.sales_id == filters["sales_id"])
        if filters.get("region"):
            query = query.filter(Customer.region == filters["region"])
        if filters.get("source_channel"):
            query = query.filter(Customer.source_channel == filters["source_channel"])
        if filters.get("keyword"):
            kw = filters["keyword"]
            from sqlalchemy import or_
            query = query.filter(
                or_(
                    Customer.name.ilike(f"%{kw}%"),
                    Customer.contact_person.ilike(f"%{kw}%"),
                    Customer.phone.ilike(f"%{kw}%"),
                    Customer.company.ilike(f"%{kw}%"),
                )
            )

    customers = query.order_by(Customer.stage_entered_at.asc()).all()

    # Group by stage
    stages = {i: [] for i in range(1, 9)}
    for c in customers:
        card = {
            "id": str(c.id),
            "name": c.name,
            "contact_person": c.contact_person,
            "phone": c.phone,
            "company": c.company,
            "region": c.region,
            "source_channel": c.source_channel,
            "sales_id": str(c.sales_id) if c.sales_id else None,
            "sales_name": c.sales.name if c.sales else None,
            "status": c.status,
            "stage": c.current_stage,
            "contract_amount": float(c.contract_amount),
            "paid_amount": float(c.paid_amount),
            "stay_days": get_stay_days(c),
            "alert_level": get_alert_level(c),
            "stage_entered_at": c.stage_entered_at.isoformat() if c.stage_entered_at else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        stage = c.current_stage
        if stage in stages:
            stages[stage].append(card)

    result = []
    for stage_num in range(1, 9):
        result.append({
            "stage": stage_num,
            "name": _get_stage_name(stage_num),
            "customers": stages[stage_num],
            "count": len(stages[stage_num]),
        })

    return result


def get_kanban_alerts(db: Session, user_id: Optional[UUID] = None) -> list[dict]:
    """Get all overdue alert customers"""
    query = db.query(Customer).filter(Customer.status == "active")

    # sales/cs only see alerts for their own customers
    if user_id is not None:
        query = query.filter(Customer.sales_id == user_id)

    customers = query.all()

    alerts = []
    for c in customers:
        alert_level = get_alert_level(c)
        if alert_level in ("warning", "danger"):
            alerts.append({
                "id": str(c.id),
                "name": c.name,
                "contact_person": c.contact_person,
                "phone": c.phone,
                "company": c.company,
                "current_stage": c.current_stage,
                "stage_name": _get_stage_name(c.current_stage),
                "stay_days": get_stay_days(c),
                "alert_level": alert_level,
                "sales_id": str(c.sales_id) if c.sales_id else None,
            })

    # Sort by alert level (danger first)
    alerts.sort(key=lambda x: (0 if x["alert_level"] == "danger" else 1, x["stay_days"]), reverse=True)
    return alerts


def _get_stage_name(stage_num: int) -> str:
    names = {
        1: "Lead",
        2: "Consult",
        3: "Contract",
        4: "Requirements",
        5: "Service",
        6: "Delivery",
        7: "Payment",
        8: "Completed",
    }
    return names.get(stage_num, "Unknown")
