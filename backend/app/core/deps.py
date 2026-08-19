from typing import Generator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db as _get_db
from app.models.user import User

security_scheme = HTTPBearer()


def get_db() -> Generator[Session, None, None]:
    yield from _get_db()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Extract and validate JWT token, return current user."""
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid access token",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

    try:
        user_id = UUID(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has been disabled",
        )
    return current_user


def check_role_admin(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


def check_customer_access(customer, current_user: User) -> bool:
    """Enforce object-level READ access to a customer:
    - admin: full access
    - sales / cs: only their own customers
    - pm: global read-only access

    Raises 403 when access is not allowed (returns True otherwise).
    """
    if current_user.role == "admin":
        return True
    if current_user.role == "pm":
        return True
    if current_user.role in ("sales", "cs") and customer.sales_id == current_user.id:
        return True
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Permission denied",
    )


def check_customer_write_access(customer, current_user: User) -> bool:
    """Enforce object-level WRITE access to a customer:
    admins may modify any customer; sales only their own. pm/cs are read-only.

    Raises 403 when access is not allowed (returns True otherwise).
    """
    if current_user.role == "admin":
        return True
    if current_user.role == "sales" and customer.sales_id == current_user.id:
        return True
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Permission denied",
    )


def check_customer_readonly(customer, current_user: User) -> bool:
    """Check if user has read-only access"""
    if current_user.role == "admin":
        return False  # not read-only, full access
    if current_user.role in ("sales", "cs"):
        return customer.sales_id == current_user.id
    if current_user.role == "pm":
        return True
    return False


def check_task_access(task, current_user: User) -> bool:
    """Check if user can access a task"""
    if current_user.role == "admin":
        return True
    if current_user.role == "sales":
        return task.customer.sales_id == current_user.id
    if current_user.role == "pm":
        return task.assignee_id == current_user.id
    return False


def check_comm_access(comm, current_user: User) -> bool:
    """Check if user can access a communication record"""
    if current_user.role == "admin":
        return True
    if current_user.role == "sales":
        return comm.customer.sales_id == current_user.id
    if current_user.role in ("pm", "cs"):
        return comm.customer.sales_id == current_user.id
    return False
