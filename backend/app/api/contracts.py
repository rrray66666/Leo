from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import check_customer_access, get_current_active_user, get_db
from app.models.contract import Contract
from app.models.customer import Customer
from app.models.user import User
from app.schemas.contract import ContractCreate, ContractUpdate

router = APIRouter(prefix="/api/v1", tags=["Contract Management"])


def _serialize_contract(c) -> dict:
    """Convert ORM Contract object to plain dict for JSON response"""
    return {
        "id": str(c.id),
        "customer_id": str(c.customer_id),
        "contract_no": c.contract_no,
        "contract_amount": float(c.contract_amount) if c.contract_amount is not None else None,
        "sign_date": c.sign_date.isoformat() if c.sign_date else None,
        "payment_terms": c.payment_terms,
        "delivery_date": c.delivery_date.isoformat() if c.delivery_date else None,
        "contract_file": c.contract_file,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


@router.post("/customers/{customer_id}/contract", response_model=dict)
def create_contract(
    customer_id: UUID,
    data: ContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create a contract"""
    if current_user.role == "sales":
        raise HTTPException(status_code=403, detail="Sales can only view contracts")
    if current_user.role not in ("admin",):
        raise HTTPException(status_code=403, detail="Permission denied")

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    contract = Contract(customer_id=customer_id, **data.model_dump())
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return {"code": 0, "message": "success", "data": _serialize_contract(contract)}


@router.get("/customers/{customer_id}/contract", response_model=dict)
def get_contract(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get customer contract"""
    from app.core.deps import check_customer_access
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    check_customer_access(customer, current_user)
    contract = (
        db.query(Contract)
        .filter(Contract.customer_id == customer_id)
        .first()
    )
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    return {"code": 0, "message": "success", "data": _serialize_contract(contract)}


@router.put("/contracts/{id}", response_model=dict)
def update_contract(
    id: UUID,
    data: ContractUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update a contract"""
    if current_user.role == "sales":
        raise HTTPException(status_code=403, detail="Sales can only view contracts")
    if current_user.role not in ("admin",):
        raise HTTPException(status_code=403, detail="Permission denied")

    contract = db.query(Contract).filter(Contract.id == id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(contract, key, value)
    db.commit()
    db.refresh(contract)
    return {"code": 0, "message": "success", "data": _serialize_contract(contract)}


@router.delete("/contracts/{id}", response_model=dict)
def delete_contract(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete a contract"""
    if current_user.role == "sales":
        raise HTTPException(status_code=403, detail="Sales can only view contracts")
    if current_user.role not in ("admin",):
        raise HTTPException(status_code=403, detail="Permission denied")

    contract = db.query(Contract).filter(Contract.id == id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    db.delete(contract)
    db.commit()
    return {"code": 0, "message": "success", "data": None}


@router.put("/contracts/{id}/file", response_model=dict)
def update_contract_file(
    id: UUID,
    file_path: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update contract file"""
    if current_user.role == "sales":
        raise HTTPException(status_code=403, detail="Sales can only view contracts")
    if current_user.role not in ("admin",):
        raise HTTPException(status_code=403, detail="Permission denied")

    contract = db.query(Contract).filter(Contract.id == id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    contract.contract_file = file_path
    db.commit()
    db.refresh(contract)
    return {"code": 0, "message": "success", "data": _serialize_contract(contract)}
