from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PaymentCreate(BaseModel):
    amount: float = Field(..., gt=0)
    payment_date: Optional[date] = None
    payment_type: str = Field(..., pattern="^(deposit|milestone|final)$")
    invoice_no: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class PaymentUpdate(BaseModel):
    amount: Optional[float] = Field(None, gt=0)
    payment_date: Optional[date] = None
    payment_type: Optional[str] = Field(None, pattern="^(deposit|milestone|final)$")
    invoice_no: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class PaymentResponse(BaseModel):
    id: UUID
    customer_id: UUID
    amount: float
    payment_date: Optional[date] = None
    payment_type: str
    invoice_no: Optional[str] = None
    notes: Optional[str] = None
    recorded_by: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
