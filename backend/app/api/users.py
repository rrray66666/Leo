from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import check_role_admin, get_current_active_user, get_db
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import (
    AdminPasswordReset,
    PasswordChange,
    UserCreate,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/api/v1/users", tags=["User Management"])


@router.post("", response_model=dict)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role_admin),
):
    """Create user (admin only)"""
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=data.name,
        email=data.email,
        phone=data.phone,
        password_hash=get_password_hash(data.password),
        role=data.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "code": 0,
        "message": "success",
        "data": UserResponse.model_validate(user).model_dump(),
    }


@router.get("", response_model=dict)
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """User list"""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return {
        "code": 0,
        "message": "success",
        "data": [UserResponse.model_validate(u).model_dump() for u in users],
    }


# NOTE: /me routes MUST be registered before /{id} routes,
# otherwise "me" would be captured by the {id} path param and fail UUID validation.


@router.get("/me", response_model=dict)
def get_my_info(
    current_user: User = Depends(get_current_active_user),
):
    """Current user info"""
    return {
        "code": 0,
        "message": "success",
        "data": UserResponse.model_validate(current_user).model_dump(),
    }


@router.put("/me", response_model=dict)
def update_my_info(
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Update personal info"""
    update_data = data.model_dump(exclude_none=True, exclude={"role", "is_active"})
    # Prevent taking an email that is already used by another user
    new_email = update_data.get("email")
    if new_email and new_email != current_user.email:
        existing = (
            db.query(User)
            .filter(User.email == new_email, User.id != current_user.id)
            .first()
        )
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")
    for key, value in update_data.items():
        setattr(current_user, key, value)
    db.commit()
    db.refresh(current_user)

    return {
        "code": 0,
        "message": "success",
        "data": UserResponse.model_validate(current_user).model_dump(),
    }


@router.put("/me/password", response_model=dict)
def change_my_password(
    data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Change own password"""
    if not verify_password(data.old_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect original password")
    current_user.password_hash = get_password_hash(data.new_password)
    db.commit()
    return {"code": 0, "message": "success", "data": None}


@router.put("/{id}", response_model=dict)
def update_user(
    id: UUID,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role_admin),
):
    """Update user (admin only)"""
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)

    return {
        "code": 0,
        "message": "success",
        "data": UserResponse.model_validate(user).model_dump(),
    }


@router.put("/{id}/password", response_model=dict)
def reset_password(
    id: UUID,
    data: AdminPasswordReset,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role_admin),
):
    """Reset user password (admin only)"""
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = get_password_hash(data.new_password)
    db.commit()
    return {"code": 0, "message": "success", "data": None}

