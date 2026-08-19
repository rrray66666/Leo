from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import check_task_access, get_current_active_user, get_db
from app.models.customer import Customer
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskStatusUpdate, TaskUpdate

router = APIRouter(prefix="/api/v1", tags=["Task Management"])


def _serialize_task(t) -> dict:
    """Convert ORM Task object to plain dict for JSON response"""
    return {
        "id": str(t.id),
        "customer_id": str(t.customer_id),
        "name": t.name,
        "description": t.description,
        "assignee_id": str(t.assignee_id) if t.assignee_id else None,
        "assignee_name": t.assignee.name if t.assignee else None,
        "status": t.status,
        "priority": t.priority,
        "start_date": t.start_date.isoformat() if t.start_date else None,
        "due_date": t.due_date.isoformat() if t.due_date else None,
        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }


@router.post("/customers/{customer_id}/tasks", response_model=dict)
def create_task(
    customer_id: UUID,
    data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Create task"""
    from app.core.deps import check_customer_write_access
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    check_customer_write_access(customer, current_user)

    task = Task(customer_id=customer_id, **data.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return {"code": 0, "message": "success", "data": _serialize_task(task)}


@router.get("/customers/{customer_id}/tasks", response_model=dict)
def list_tasks(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List customer tasks"""
    from app.core.deps import check_customer_access
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    check_customer_access(customer, current_user)
    tasks = (
        db.query(Task)
        .filter(Task.customer_id == customer_id)
        .order_by(Task.created_at.desc())
        .all()
    )
    data = [_serialize_task(t) for t in tasks]
    return {"code": 0, "message": "success", "data": data}


@router.get("/tasks/{id}", response_model=dict)
def get_task(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get task detail"""
    task = db.query(Task).filter(Task.id == id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not check_task_access(task, current_user):
        raise HTTPException(status_code=403, detail="Permission denied")
    return {"code": 0, "message": "success", "data": _serialize_task(task)}


@router.put("/tasks/{id}", response_model=dict)
def update_task(
    id: UUID,
    data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update task"""
    if current_user.role == "sales":
        raise HTTPException(status_code=403, detail="Sales can only view tasks")
    task = db.query(Task).filter(Task.id == id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not check_task_access(task, current_user):
        raise HTTPException(status_code=403, detail="Permission denied")
    if current_user.role not in ("admin", "pm"):
        raise HTTPException(status_code=403, detail="Permission denied")

    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(task, key, value)
    db.commit()
    db.refresh(task)
    return {"code": 0, "message": "success", "data": _serialize_task(task)}


@router.patch("/tasks/{id}/status", response_model=dict)
def update_task_status(
    id: UUID,
    data: TaskStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update task status"""
    if current_user.role == "sales":
        raise HTTPException(status_code=403, detail="Sales can only view tasks")
    task = db.query(Task).filter(Task.id == id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not check_task_access(task, current_user):
        raise HTTPException(status_code=403, detail="Permission denied")
    if current_user.role not in ("admin", "pm"):
        raise HTTPException(status_code=403, detail="Permission denied")

    task.status = data.status
    if data.status == "completed":
        task.completed_at = data.completed_at or datetime.now(timezone.utc)
    db.commit()
    db.refresh(task)
    return {"code": 0, "message": "success", "data": _serialize_task(task)}


@router.patch("/tasks/{id}/assignee", response_model=dict)
def update_task_assignee(
    id: UUID,
    assignee_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update task assignee"""
    if current_user.role == "sales":
        raise HTTPException(status_code=403, detail="Sales can only view tasks")
    task = db.query(Task).filter(Task.id == id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not check_task_access(task, current_user):
        raise HTTPException(status_code=403, detail="Permission denied")
    if current_user.role not in ("admin", "pm"):
        raise HTTPException(status_code=403, detail="Permission denied")
    task.assignee_id = assignee_id
    db.commit()
    db.refresh(task)
    return {"code": 0, "message": "success", "data": _serialize_task(task)}


@router.delete("/tasks/{id}", response_model=dict)
def delete_task(
    id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Delete task"""
    if current_user.role == "sales":
        raise HTTPException(status_code=403, detail="Sales can only view tasks")
    task = db.query(Task).filter(Task.id == id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not check_task_access(task, current_user):
        raise HTTPException(status_code=403, detail="Permission denied")
    if current_user.role not in ("admin", "pm"):
        raise HTTPException(status_code=403, detail="Permission denied")
    db.delete(task)
    db.commit()
    return {"code": 0, "message": "success", "data": None}
