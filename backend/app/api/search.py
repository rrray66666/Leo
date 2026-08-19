from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user, get_db
from app.models.customer import Customer
from app.models.user import User
from app.services.stage_service import get_alert_level, get_stay_days

router = APIRouter(prefix="/api/v1/search", tags=["Search"])


@router.get("/global", response_model=dict)
def global_search(
    keyword: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Global search for customers"""
    query = db.query(Customer).filter(
        Customer.status != "deleted",  # hide soft-deleted customers
        or_(
            Customer.name.ilike(f"%{keyword}%"),
            Customer.contact_person.ilike(f"%{keyword}%"),
            Customer.phone.ilike(f"%{keyword}%"),
            Customer.wechat.ilike(f"%{keyword}%"),
            Customer.company.ilike(f"%{keyword}%"),
        )
    )

    # sales/cs can only search their own customers; admin/pm see everything
    if current_user.role in ("sales", "cs"):
        query = query.filter(Customer.sales_id == current_user.id)

    total = query.count()
    customers = (
        query.order_by(Customer.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for c in customers:
        items.append({
            "id": str(c.id),
            "name": c.name,
            "contact_person": c.contact_person,
            "phone": c.phone,
            "wechat": c.wechat,
            "company": c.company,
            "region": c.region,
            "current_stage": c.current_stage,
            "status": c.status,
            "stay_days": get_stay_days(c),
            "alert_level": get_alert_level(c),
        })

    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }
