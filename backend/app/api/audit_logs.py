from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user, get_db
from app.models.audit_log import AuditLog
from app.models.user import User

router = APIRouter(prefix="/api/v1", tags=["Audit Logs"])


def _serialize_log(log: AuditLog) -> dict:
    """Serialize an audit log into the frontend-friendly shape"""
    changes = {}
    before = log.before_data or {}
    after = log.after_data or {}
    for key in set(before.keys()) | set(after.keys()):
        if before.get(key) != after.get(key):
            changes[key] = {"old": before.get(key), "new": after.get(key)}

    return {
        "id": str(log.id),
        "created_at": log.created_at.isoformat() if log.created_at else None,
        "operator_name": log.user.name if log.user else "System",
        "action": log.action,
        "resource_type": log.object_type,
        "resource_id": str(log.object_id) if log.object_id else None,
        "customer_id": str(log.customer_id) if log.customer_id else None,
        "description": f"{log.action.replace('_', ' ')} {log.object_type}",
        "changes": changes,
        "ip_address": log.ip_address,
    }


@router.get("/audit-logs", response_model=dict)
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: Optional[str] = Query(None),
    object_type: Optional[str] = Query(None),
    operator_name: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List audit logs"""
    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action)
    if object_type:
        query = query.filter(AuditLog.object_type == object_type)
    if operator_name:
        query = query.join(User, AuditLog.user_id == User.id).filter(
            User.name.ilike(f"%{operator_name}%")
        )
    if start_date:
        try:
            start = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
            query = query.filter(AuditLog.created_at >= start)
        except ValueError:
            pass
    if end_date:
        try:
            end = datetime.fromisoformat(end_date).replace(tzinfo=timezone.utc)
            query = query.filter(AuditLog.created_at <= end)
        except ValueError:
            pass

    total = query.count()
    logs = (
        query.order_by(AuditLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "code": 0,
        "message": "success",
        "data": {
            "items": [_serialize_log(log) for log in logs],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.get("/customers/{customer_id}/audit-logs", response_model=dict)
def customer_audit_logs(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Customer audit logs"""
    logs = (
        db.query(AuditLog)
        .filter(AuditLog.customer_id == customer_id)
        .order_by(AuditLog.created_at.desc())
        .all()
    )
    return {
        "code": 0,
        "message": "success",
        "data": [_serialize_log(log) for log in logs],
    }
