from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TaskCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    assignee_id: Optional[UUID] = None
    status: str = Field(default="pending", pattern="^(pending|in_progress|completed)$")
    priority: str = Field(default="medium", pattern="^(low|medium|high|urgent)$")
    start_date: Optional[date] = None
    due_date: Optional[date] = None


class TaskUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    assignee_id: Optional[UUID] = None
    status: Optional[str] = Field(None, pattern="^(pending|in_progress|completed)$")
    priority: Optional[str] = Field(None, pattern="^(low|medium|high|urgent)$")
    start_date: Optional[date] = None
    due_date: Optional[date] = None


class TaskStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(pending|in_progress|completed)$")
    completed_at: Optional[datetime] = None


class TaskResponse(BaseModel):
    id: UUID
    customer_id: UUID
    name: str
    description: Optional[str] = None
    assignee_id: Optional[UUID] = None
    status: str
    priority: str
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
