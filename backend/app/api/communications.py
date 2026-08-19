from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import check_comm_access, get_current_active_user, get_db
from app.models.communication import Communication
from app.models.customer import Customer
from app.models.user import User
from app.schemas.communication import CommunicationCreate, CommunicationUpdate

router = APIRouter(prefix="/api/v1", tags=["Communications"])


def _serialize_communication(c) -> dict:
    """Convert ORM Communication object to plain dict for JSON response"""
    return {
        "id": str(c.id),
        "customer_id": str(c.customer_id),
        "user_id": str(c.user_id) if c.user_id else None,
        "user_name": c.user.name if c.user else None,
        "channel": c.channel,
        "content": c.content,
        "next_action": c.next_action,
        "next_action_date": c.next_action_date.isoformat() if c.next_action_date else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@router.post("/customers/{customer_id}/communications", response_model=dict)
def create_communication(
    customer_id: UUID,
    data: CommunicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a communication record"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if current_user.role == "admin":
        pass
    elif current_user.role == "sales":
        if customer.sales_id != current_user.id:
            raise HTTPException(status_code=403, detail="Permission denied")
    elif current_user.role in ("pm", "cs"):
        pass  # Assigned access
    else:
        raise HTTPException(status_code=403, detail="Permission denied")

    comm = Communication(
        customer_id=customer_id,
        user_id=current_user.id,
        **data.model_dump(),
    )
    db.add(comm)
    db.commit()
    db.refresh(comm)
    return {"code": 0, "message": "success", "data": _serialize_communication(comm)}


@router.get("/customers/{customer_id}/communications", response_model=dict)
def list_communications(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List communication records for a customer"""
    from app.core.deps import check_customer_access
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    check_customer_access(customer, current_user)
    comms = (
        db.query(Communication)
        .filter(Communication.customer_id == customer_id)
        .order_by(Communication.created_at.desc())
        .all()
    )
    data = []
    for c in comms:
        data.append({
            "id": str(c.id),
            "customer_id": str(c.customer_id),
            "user_id": str(c.user_id) if c.user_id else None,
            "user_name": c.user.name if c.user else None,
            "channel": c.channel,
            "content": c.content,
            "next_action": c.next_action,
            "next_action_date": c.next_action_date.isoformat() if c.next_action_date else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })
    return {"code": 0, "message": "success", "data": data}


@router.put("/communications/{id}", response_model=dict)
def update_communication(
    id: UUID,
    data: CommunicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a communication record"""
    comm = db.query(Communication).filter(Communication.id == id).first()
    if not comm:
        raise HTTPException(status_code=404, detail="Communication record not found")
    if not check_comm_access(comm, current_user):
        raise HTTPException(status_code=403, detail="Permission denied")

    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(comm, key, value)
    db.commit()
    db.refresh(comm)
    return {"code": 0, "message": "success", "data": _serialize_communication(comm)}


@router.delete("/communications/{id}", response_model=dict)
def delete_communication(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a communication record"""
    comm = db.query(Communication).filter(Communication.id == id).first()
    if not comm:
        raise HTTPException(status_code=404, detail="Communication record not found")
    if not check_comm_access(comm, current_user):
        raise HTTPException(status_code=403, detail="Permission denied")
    db.delete(comm)
    db.commit()
    return {"code": 0, "message": "success", "data": None}
