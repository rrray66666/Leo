from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ContractCreate(BaseModel):
    contract_no: str = Field(..., max_length=50)
    contract_amount: Optional[float] = None
    sign_date: Optional[date] = None
    payment_terms: Optional[str] = None
    delivery_date: Optional[date] = None
    contract_file: Optional[str] = None


class ContractUpdate(BaseModel):
    contract_no: Optional[str] = Field(None, max_length=50)
    contract_amount: Optional[float] = None
    sign_date: Optional[date] = None
    payment_terms: Optional[str] = None
    delivery_date: Optional[date] = None
    contract_file: Optional[str] = None


class ContractResponse(BaseModel):
    id: UUID
    customer_id: UUID
    contract_no: str
    contract_amount: Optional[float] = None
    sign_date: Optional[date] = None
    payment_terms: Optional[str] = None
    delivery_date: Optional[date] = None
    contract_file: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
