from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def log_action(
    db: Session,
    user_id: Optional[UUID],
    action: str,
    object_type: str,
    object_id: Optional[UUID] = None,
    customer_id: Optional[UUID] = None,
    before_data: Optional[dict] = None,
    after_data: Optional[dict] = None,
    ip_address: Optional[str] = None,
) -> AuditLog:
    """Record an audit log"""
    log = AuditLog(
        user_id=user_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        customer_id=customer_id,
        before_data=before_data,
        after_data=after_data,
        ip_address=ip_address,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log
