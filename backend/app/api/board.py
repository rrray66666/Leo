from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user, get_db
from app.models.user import User
from app.services.board_service import get_kanban_alerts, get_kanban_data

router = APIRouter(prefix="/api/v1/board", tags=["Board"])


@router.get("/kanban", response_model=dict)
def kanban(
    sales_id: Optional[UUID] = Query(None),
    region: Optional[str] = Query(None),
    source_channel: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get kanban data"""
    filters = {}
    if sales_id:
        filters["sales_id"] = sales_id
    if region:
        filters["region"] = region
    if source_channel:
        filters["source_channel"] = source_channel
    if keyword:
        filters["keyword"] = keyword

    # sales/cs only see their own customers; admin/pm see everything
    user_id = current_user.id if current_user.role in ("sales", "cs") else None
    data = get_kanban_data(db, user_id, filters)
    return {"code": 0, "message": "success", "data": data}


@router.get("/alerts", response_model=dict)
def alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get alert list"""
    user_id = current_user.id if current_user.role in ("sales", "cs") else None
    data = get_kanban_alerts(db, user_id)
    return {"code": 0, "message": "success", "data": data}
