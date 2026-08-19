from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import check_role_admin, get_current_active_user, get_db
from app.models.dict_item import DictItem
from app.models.user import User

router = APIRouter(prefix="/api/v1/dict", tags=["Data Dictionary"])


def _get_dict_items(db: Session, category: str) -> list[dict]:
    items = (
        db.query(DictItem)
        .filter(DictItem.category == category, DictItem.is_active == True)
        .order_by(DictItem.sort_order.asc())
        .all()
    )
    return [{"id": str(i.id), "name": i.name, "code": i.code} for i in items]


def _update_dict_items(db: Session, category: str, items: list[dict]) -> None:
    """Replace all dict items for a given category"""
    db.query(DictItem).filter(DictItem.category == category).delete()
    for item in items:
        db.add(
            DictItem(
                category=category,
                name=item.get("name"),
                code=item.get("code"),
                sort_order=item.get("sort_order", 0),
                is_active=True,
            )
        )
    db.commit()


@router.get("/industries", response_model=dict)
def get_industries(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get industry list"""
    return {"code": 0, "message": "success", "data": _get_dict_items(db, "industry")}


@router.get("/regions", response_model=dict)
def get_regions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get region list"""
    return {"code": 0, "message": "success", "data": _get_dict_items(db, "region")}


@router.get("/channels", response_model=dict)
def get_channels(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get channel list"""
    return {"code": 0, "message": "success", "data": _get_dict_items(db, "channel")}


@router.get("/categories", response_model=dict)
def get_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get document category list"""
    return {"code": 0, "message": "success", "data": _get_dict_items(db, "document_category")}


@router.put("/industries", response_model=dict)
def update_industries(
    items: list[dict],
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role_admin),
):
    """Update industry list (admin only)"""
    _update_dict_items(db, "industry", items)
    return {"code": 0, "message": "success", "data": None}


@router.put("/regions", response_model=dict)
def update_regions(
    items: list[dict],
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role_admin),
):
    """Update region list (admin only)"""
    _update_dict_items(db, "region", items)
    return {"code": 0, "message": "success", "data": None}


@router.put("/channels", response_model=dict)
def update_channels(
    items: list[dict],
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role_admin),
):
    """Update channel list (admin only)"""
    _update_dict_items(db, "channel", items)
    return {"code": 0, "message": "success", "data": None}


@router.put("/categories", response_model=dict)
def update_categories(
    items: list[dict],
    db: Session = Depends(get_db),
    current_user: User = Depends(check_role_admin),
):
    """Update document category list (admin only)"""
    _update_dict_items(db, "document_category", items)
    return {"code": 0, "message": "success", "data": None}
