from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    email: str = Field(..., max_length=100)
    phone: str = Field(..., max_length=20)
    password: str = Field(..., min_length=6, max_length=100)
    role: str = Field(..., pattern="^(admin|sales|pm|cs)$")


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    is_active: Optional[bool] = None
    role: Optional[str] = Field(None, pattern="^(admin|sales|pm|cs)$")


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    phone: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UserLogin(BaseModel):
    email: str = Field(..., max_length=100)
    password: str = Field(..., min_length=1)


class UserRegister(BaseModel):
    name: str = Field(..., min_length=2, max_length=50)
    email: str = Field(..., max_length=100)
    phone: str = Field("", max_length=20)
    password: str = Field(..., min_length=6, max_length=100)


class PasswordChange(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=100)


class AdminPasswordReset(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=100)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[UUID] = None
    role: Optional[str] = None
