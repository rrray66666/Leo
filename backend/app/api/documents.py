import os
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.deps import check_customer_access, get_current_active_user, get_db
from app.models.customer import Customer
from app.models.document import Document
from app.models.user import User
from app.schemas.document import DocumentUpdate

router = APIRouter(prefix="/api/v1", tags=["Document Management"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")


def _serialize_document(d) -> dict:
    """Convert ORM Document object to plain dict for JSON response"""
    return {
        "id": str(d.id),
        "customer_id": str(d.customer_id),
        "file_name": d.file_name,
        "file_path": d.file_path,
        "file_size": d.file_size,
        "file_type": d.file_type,
        "category": d.category,
        "uploaded_by": str(d.uploaded_by) if d.uploaded_by else None,
        "uploaded_by_name": d.uploader.name if d.uploader else None,
        "created_at": d.created_at.isoformat() if d.created_at else None,
    }


def _check_document_write_access(customer, current_user):
    """Check user can write documents for this customer"""
    if current_user.role == "admin":
        return True
    if current_user.role in ("sales", "cs"):
        raise HTTPException(status_code=403, detail="Read-only access to documents")
    if current_user.role == "pm":
        return True
    return True


@router.post("/customers/{customer_id}/documents", response_model=dict)
async def upload_document(
    customer_id: UUID,
    file: UploadFile = File(...),
    category: str = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Upload document"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    _check_document_write_access(customer, current_user)

    # Save file to local storage (strip path components from the client-provided
    # filename to prevent directory traversal)
    customer_dir = os.path.join(UPLOAD_DIR, str(customer_id))
    os.makedirs(customer_dir, exist_ok=True)

    safe_name = os.path.basename(file.filename or "unnamed")
    file_path = os.path.join(customer_dir, safe_name)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    doc = Document(
        customer_id=customer_id,
        file_name=safe_name,
        file_path=file_path,
        file_size=len(content),
        file_type=safe_name.split(".")[-1] if "." in safe_name else None,
        category=category,
        uploaded_by=current_user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"code": 0, "message": "success", "data": _serialize_document(doc)}


@router.get("/customers/{customer_id}/documents", response_model=dict)
def list_documents(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List customer documents"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    check_customer_access(customer, current_user)
    docs = (
        db.query(Document)
        .filter(Document.customer_id == customer_id)
        .order_by(Document.created_at.desc())
        .all()
    )
    data = [_serialize_document(d) for d in docs]
    return {"code": 0, "message": "success", "data": data}


@router.get("/documents/{id}", response_model=dict)
def get_document(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get document detail"""
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    customer = db.query(Customer).filter(Customer.id == doc.customer_id).first()
    if customer:
        check_customer_access(customer, current_user)
    return {"code": 0, "message": "success", "data": _serialize_document(doc)}


@router.get("/documents/{id}/download", response_model=dict)
def download_document(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Download document"""
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    customer = db.query(Customer).filter(Customer.id == doc.customer_id).first()
    if customer:
        check_customer_access(customer, current_user)
    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")
    return FileResponse(
        path=doc.file_path,
        filename=doc.file_name,
        media_type="application/octet-stream",
    )


@router.put("/documents/{id}", response_model=dict)
def update_document_info(
    id: UUID,
    data: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update document info"""
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    customer = db.query(Customer).filter(Customer.id == doc.customer_id).first()
    if customer:
        _check_document_write_access(customer, current_user)

    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(doc, key, value)
    db.commit()
    db.refresh(doc)
    return {"code": 0, "message": "success", "data": _serialize_document(doc)}


@router.put("/documents/{id}/file", response_model=dict)
async def replace_document_file(
    id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Replace document file"""
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    customer = db.query(Customer).filter(Customer.id == doc.customer_id).first()
    if customer:
        _check_document_write_access(customer, current_user)

    # Delete old file
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)

    # Save new file (strip path components to prevent directory traversal)
    customer_dir = os.path.join(UPLOAD_DIR, str(doc.customer_id))
    os.makedirs(customer_dir, exist_ok=True)

    safe_name = os.path.basename(file.filename or "unnamed")
    new_path = os.path.join(customer_dir, safe_name)
    content = await file.read()
    with open(new_path, "wb") as f:
        f.write(content)

    doc.file_name = safe_name
    doc.file_path = new_path
    doc.file_size = len(content)
    doc.file_type = safe_name.split(".")[-1] if "." in safe_name else None
    db.commit()
    db.refresh(doc)
    return {"code": 0, "message": "success", "data": _serialize_document(doc)}


@router.delete("/documents/{id}", response_model=dict)
def delete_document(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete document"""
    doc = db.query(Document).filter(Document.id == id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    customer = db.query(Customer).filter(Customer.id == doc.customer_id).first()
    if customer:
        _check_document_write_access(customer, current_user)
    # Delete actual file
    if os.path.exists(doc.file_path):
        os.remove(doc.file_path)
    db.delete(doc)
    db.commit()
    return {"code": 0, "message": "success", "data": None}
