from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CustomerCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    contact_person: str = Field(..., max_length=50)
    phone: str = Field(..., max_length=20)
    wechat: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    company: Optional[str] = Field(None, max_length=200)
    region: Optional[str] = Field(None, max_length=50)
    source_channel: Optional[str] = Field(None, max_length=50)
    sales_id: Optional[UUID] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    contact_person: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    wechat: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=100)
    company: Optional[str] = Field(None, max_length=200)
    region: Optional[str] = Field(None, max_length=50)
    source_channel: Optional[str] = Field(None, max_length=50)
    sales_id: Optional[UUID] = None


class CustomerResponse(BaseModel):
    id: UUID
    name: str
    contact_person: Optional[str] = None
    phone: str
    wechat: Optional[str] = None
    email: Optional[str] = None
    company: Optional[str] = None
    region: Optional[str] = None
    source_channel: Optional[str] = None
    sales_id: Optional[UUID] = None
    current_stage: int
    stage_entered_at: Optional[datetime] = None
    contract_amount: float = 0
    paid_amount: float = 0
    status: str = "active"
    lost_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    stay_days: int = 0
    alert_level: str = "normal"

    class Config:
        from_attributes = True


class StageAdvance(BaseModel):
    new_stage: int = Field(..., ge=1, le=8)
    remark: str = ""


class StatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(active|lost|completed|terminated)$")
    lost_reason: Optional[str] = None


class BatchAssign(BaseModel):
    customer_ids: list[UUID]
    new_sales_id: UUID


class BatchStatus(BaseModel):
    customer_ids: list[UUID]
    status: str = Field(..., pattern="^(active|lost|completed|terminated)$")


class CustomerSearch(BaseModel):
    keyword: str = Field(..., min_length=1)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
