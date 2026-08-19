from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentResponse(BaseModel):
    id: UUID
    customer_id: UUID
    file_name: str
    file_path: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    category: Optional[str] = None
    uploaded_by: Optional[UUID] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DocumentUpdate(BaseModel):
    file_name: Optional[str] = Field(None, max_length=200)
    category: Optional[str] = Field(None, max_length=50)
