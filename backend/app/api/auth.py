from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.core.deps import get_current_active_user, get_db
from app.models.user import User
from app.schemas.user import (
    PasswordChange,
    Token,
    UserLogin,
    UserRegister,
    UserResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/login", response_model=dict)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """User login"""
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User has been disabled",
        )

    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {
        "code": 0,
        "message": "success",
        "data": {
            "access_token": token,
            "token_type": "bearer",
            "user": UserResponse.model_validate(user).model_dump(),
        },
    }


@router.post("/register", response_model=dict)
def register(
    data: UserRegister,
    db: Session = Depends(get_db),
):
    """User registration - creates a new account and stores it in the database"""
    # Check email uniqueness
    existing_email = db.query(User).filter(User.email == data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    # Check phone uniqueness (if provided)
    if data.phone:
        existing_phone = db.query(User).filter(User.phone == data.phone).first()
        if existing_phone:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered",
            )

    # Create user (default role: sales, registered users can be upgraded by admin)
    user = User(
        name=data.name,
        email=data.email,
        phone=data.phone,
        password_hash=get_password_hash(data.password),
        role="sales",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Auto-login: return tokens
    access_token = create_access_token({"sub": str(user.id), "role": user.role})
    return {
        "code": 0,
        "message": "success",
        "data": {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "name": user.name,
                "email": user.email,
                "role": user.role,
            },
        },
    }


@router.post("/refresh", response_model=dict)
def refresh(token_data: Token, db: Session = Depends(get_db)):
    """Refresh token"""
    try:
        payload = decode_access_token(token_data.access_token)
        user = db.query(User).filter(User.id == UUID(payload.get("sub"))).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or disabled",
            )
        new_token = create_access_token(
            data={"sub": str(user.id), "role": user.role}
        )
        return {
            "code": 0,
            "message": "success",
            "data": {"access_token": new_token, "token_type": "bearer"},
        }
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )


@router.get("/me", response_model=dict)
def get_me(current_user: User = Depends(get_current_active_user)):
    """Get current user info"""
    return {
        "code": 0,
        "message": "success",
        "data": UserResponse.model_validate(current_user).model_dump(),
    }
