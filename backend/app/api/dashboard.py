from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user, get_db
from app.models.customer import Customer
from app.models.payment import Payment
from app.models.task import Task
from app.models.user import User
from app.services.stage_service import get_alert_level, get_stay_days

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=dict)
def stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Basic statistics"""
    total_customers = db.query(Customer).count()
    active_customers = db.query(Customer).filter(Customer.status == "active").count()

    # Count by stage
    stage_counts = {}
    for stage in range(1, 9):
        count = (
            db.query(Customer)
            .filter(Customer.current_stage == stage, Customer.status == "active")
            .count()
        )
        stage_counts[f"stage_{stage}"] = count

    # Overdue count
    overdue_count = 0
    all_active = db.query(Customer).filter(Customer.status == "active").all()
    for c in all_active:
        if get_alert_level(c) in ("warning", "danger"):
            overdue_count += 1

    # Today's new customers
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    today_new = (
        db.query(Customer)
        .filter(Customer.created_at >= today_start)
        .count()
    )

    # New customers this month
    month_start = today_start.replace(day=1)
    monthly_new = (
        db.query(Customer)
        .filter(Customer.created_at >= month_start)
        .count()
    )

    # Payments this month
    monthly_payment = (
        db.query(func.sum(Payment.amount))
        .filter(Payment.created_at >= month_start)
        .scalar() or 0
    )

    return {
        "code": 0,
        "message": "success",
        "data": {
            "total_customers": total_customers,
            "active_customers": active_customers,
            "stage_counts": stage_counts,
            "overdue_count": overdue_count,
            "today_new": today_new,
            "monthly_new": monthly_new,
            "monthly_payment": float(monthly_payment),
        },
    }


@router.get("/funnel", response_model=dict)
def funnel(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Funnel data"""
    stage_names = {
        1: "Lead", 2: "Consult", 3: "Contract",
        4: "Requirements", 5: "Service", 6: "Delivery",
        7: "Payment", 8: "Completed",
    }

    funnel_data = []
    for stage in range(1, 9):
        count = (
            db.query(Customer)
            .filter(Customer.current_stage >= stage, Customer.status == "active")
            .count()
        )
        funnel_data.append({
            "stage": stage,
            "name": stage_names[stage],
            "count": count,
        })

    return {"code": 0, "message": "success", "data": funnel_data}


@router.get("/sales", response_model=dict)
def sales_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Sales workload statistics"""
    sales_users = db.query(User).filter(User.role.in_(["sales", "admin"])).all()
    result = []
    for user in sales_users:
        customer_count = (
            db.query(Customer)
            .filter(Customer.sales_id == user.id, Customer.status == "active")
            .count()
        )
        result.append({
            "user_id": str(user.id),
            "user_name": user.name,
            "customer_count": customer_count,
        })

    return {"code": 0, "message": "success", "data": result}


@router.get("/payments", response_model=dict)
def payment_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Payment statistics"""
    # Current month payments
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_paid = (
        db.query(func.sum(Payment.amount))
        .scalar() or 0
    )
    month_paid = (
        db.query(func.sum(Payment.amount))
        .filter(Payment.created_at >= month_start)
        .scalar() or 0
    )
    total_contract_amount = (
        db.query(func.sum(Customer.contract_amount))
        .filter(Customer.status == "active")
        .scalar() or 0
    )

    return {
        "code": 0,
        "message": "success",
        "data": {
            "total_paid": float(total_paid),
            "month_paid": float(month_paid),
            "total_contract_amount": float(total_contract_amount),
            "collection_rate": float(total_paid / total_contract_amount * 100) if total_contract_amount > 0 else 0,
        },
    }


@router.get("/payment-trend", response_model=dict)
def payment_trend(
    year: int = Query(datetime.now(timezone.utc).year, ge=2000, le=2100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Monthly payment trend for a given year"""
    trend = []
    for month in range(1, 13):
        start = datetime(year, month, 1, tzinfo=timezone.utc)
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc) if month < 12 else datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        total = (
            db.query(func.sum(Payment.amount))
            .filter(Payment.payment_date >= start.date(), Payment.payment_date < end.date())
            .scalar() or 0
        )
        trend.append({
            "month": f"{year}-{month:02d}",
            "total": float(total),
        })
    return {"code": 0, "message": "success", "data": trend}
