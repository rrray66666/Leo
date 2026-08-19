from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import check_customer_access, get_current_active_user, get_db
from app.models.customer import Customer
from app.models.payment import Payment
from app.models.user import User
from app.schemas.payment import PaymentCreate, PaymentUpdate

router = APIRouter(prefix="/api/v1", tags=["Payment Management"])


def _serialize_payment(p) -> dict:
    """Convert ORM Payment object to plain dict for JSON response"""
    return {
        "id": str(p.id),
        "customer_id": str(p.customer_id),
        "amount": float(p.amount) if p.amount is not None else None,
        "payment_date": p.payment_date.isoformat() if p.payment_date else None,
        "payment_type": p.payment_type,
        "invoice_no": p.invoice_no,
        "notes": p.notes,
        "recorded_by": str(p.recorded_by) if p.recorded_by else None,
        "recorded_by_name": p.recorder.name if p.recorder else None,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


@router.post("/customers/{customer_id}/payments", response_model=dict)
def create_payment(
    customer_id: UUID,
    data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create payment record"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    payment = Payment(
        customer_id=customer_id,
        recorded_by=current_user.id,
        **data.model_dump(),
    )
    db.add(payment)
    db.flush()

    # Update customer paid amount
    customer.paid_amount = float(customer.paid_amount or 0) + float(payment.amount)
    db.commit()
    db.refresh(payment)
    return {"code": 0, "message": "success", "data": _serialize_payment(payment)}


@router.get("/customers/{customer_id}/payments", response_model=dict)
def list_payments(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List customer payment records"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    check_customer_access(customer, current_user)
    payments = (
        db.query(Payment)
        .filter(Payment.customer_id == customer_id)
        # MySQL sorts NULL values last by default in DESC order (no NULLS LAST syntax support)
        .order_by(Payment.payment_date.desc(), Payment.created_at.desc())
        .all()
    )
    return {"code": 0, "message": "success", "data": [_serialize_payment(x) for x in payments]}


@router.put("/payments/{id}", response_model=dict)
def update_payment(
    id: UUID,
    data: PaymentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update payment record"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")

    payment = db.query(Payment).filter(Payment.id == id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    old_amount = float(payment.amount)
    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(payment, key, value)
    db.flush()

    # Update customer paid amount difference
    customer = db.query(Customer).filter(Customer.id == payment.customer_id).first()
    if customer:
        new_amount = float(payment.amount)
        customer.paid_amount = float(customer.paid_amount or 0) - old_amount + new_amount

    db.commit()
    db.refresh(payment)
    return {"code": 0, "message": "success", "data": _serialize_payment(payment)}


@router.delete("/payments/{id}", response_model=dict)
def delete_payment(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete payment record"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Permission denied")

    payment = db.query(Payment).filter(Payment.id == id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")

    # Update customer paid amount
    customer = db.query(Customer).filter(Customer.id == payment.customer_id).first()
    if customer:
        customer.paid_amount = float(customer.paid_amount or 0) - float(payment.amount)

    db.delete(payment)
    db.commit()
    return {"code": 0, "message": "success", "data": None}
