from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CommunicationCreate(BaseModel):
    channel: str = Field(..., pattern="^(phone|wechat|meeting|email)$")
    content: Optional[str] = None
    next_action: Optional[str] = None
    next_action_date: Optional[date] = None


class CommunicationUpdate(BaseModel):
    channel: Optional[str] = Field(None, pattern="^(phone|wechat|meeting|email)$")
    content: Optional[str] = None
    next_action: Optional[str] = None
    next_action_date: Optional[date] = None


class CommunicationResponse(BaseModel):
    id: UUID
    customer_id: UUID
    user_id: Optional[UUID] = None
    channel: str
    content: Optional[str] = None
    next_action: Optional[str] = None
    next_action_date: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
