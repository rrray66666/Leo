from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.stage_history import StageHistory
from app.models.task import Task


class STAGES:
    """Stage configuration constants"""
    STAGE_NAMES = {
        1: "Lead",
        2: "Consult",
        3: "Contract",
        4: "Requirements",
        5: "Service",
        6: "Delivery",
        7: "Payment",
        8: "Completed",
    }

    BASE_DAYS = {1: 7, 2: 14, 3: 7, 4: 14, 5: 30, 6: 14, 7: 30, 8: 0}
    ALERT_DAYS = {1: 14, 2: 21, 3: 14, 4: 21, 5: 45, 6: 21, 7: 45, 8: 0}


def get_stay_days(customer: Customer) -> int:
    """Calculate days the customer has stayed in the current stage"""
    if not customer.stage_entered_at:
        return 0
    entered_at = customer.stage_entered_at
    # MySQL DATETIME columns are returned as naive datetimes; treat them as UTC.
    if entered_at.tzinfo is None:
        entered_at = entered_at.replace(tzinfo=timezone.utc)
    delta = datetime.now(timezone.utc) - entered_at
    return delta.days


def get_alert_level(customer: Customer) -> str:
    """Get alert level: normal / warning / danger"""
    stay_days = get_stay_days(customer)
    stage = customer.current_stage
    base_days = STAGES.BASE_DAYS.get(stage, 7)
    alert_days = STAGES.ALERT_DAYS.get(stage, 14)

    if stay_days >= alert_days:
        return "danger"
    elif stay_days >= base_days:
        return "warning"
    return "normal"


def _check_prerequisites(db: Session, customer: Customer, new_stage: int) -> None:
    """Prerequisite check"""
    # Stage 2→3 requires signed contract
    if customer.current_stage == 2 and new_stage == 3:
        contract = db.query(Customer).filter(Customer.id == customer.id).first()
        # Check if there is a signed contract
        from app.models.contract import Contract
        signed_contract = (
            db.query(Contract)
            .filter(
                Contract.customer_id == customer.id,
                Contract.sign_date.isnot(None),
            )
            .first()
        )
        if not signed_contract:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please sign a contract before advancing to Contract stage",
            )

    # Stage 5→6 requires all tasks completed
    if customer.current_stage == 5 and new_stage == 6:
        pending_tasks = (
            db.query(Task)
            .filter(
                Task.customer_id == customer.id,
                Task.status != "completed",
            )
            .count()
        )
        if pending_tasks > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please complete all tasks before advancing to Delivery stage",
            )

    # Stage 6→7 requires customer acceptance confirmation (checked via acceptance documents)
    if customer.current_stage == 6 and new_stage == 7:
        from app.models.document import Document
        acceptance_docs = (
            db.query(Document)
            .filter(
                Document.customer_id == customer.id,
                Document.category == "acceptance",
            )
            .count()
        )
        if acceptance_docs == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please upload customer acceptance documents before advancing to Payment stage",
            )

    # Stage 7→8 requires full payment
    if customer.current_stage == 7 and new_stage == 8:
        if customer.paid_amount < customer.contract_amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please ensure full payment is received before advancing to Completed stage",
            )


def advance_stage(
    db: Session,
    customer_id: UUID,
    new_stage: int,
    operator_id: UUID,
    remark: str = "",
) -> Customer:
    """Advance customer stage"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    # Validate stage range
    if new_stage < 1 or new_stage > 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid stage number",
        )

    # Validate sequential advancement only
    if new_stage != customer.current_stage + 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Stages can only advance sequentially, current stage is {customer.current_stage} ({STAGES.STAGE_NAMES.get(customer.current_stage, 'Unknown')}), can only advance to the next stage",
        )

    # Validate customer status
    if customer.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Customer status is '{customer.status}', cannot advance stage. Only active customers can advance.",
        )

    # Record old stage
    old_stage = customer.current_stage

    # Prerequisite check
    _check_prerequisites(db, customer, new_stage)

    # Update customer stage
    customer.current_stage = new_stage
    customer.stage_entered_at = datetime.now(timezone.utc)

    # If reaching final stage, update status
    if new_stage == 8:
        customer.status = "completed"

    # Record stage history
    history = StageHistory(
        customer_id=customer_id,
        from_stage=old_stage,
        to_stage=new_stage,
        changed_by=operator_id,
        remark=remark,
    )
    db.add(history)
    db.commit()
    db.refresh(customer)

    return customer


def rollback_stage(
    db: Session,
    customer_id: UUID,
    operator_id: UUID,
    remark: str = "",
) -> Customer:
    """Rollback customer to the previous stage (admin only)"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    # Validate not at stage 1
    if customer.current_stage <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot rollback from the first stage",
        )

    # Validate not completed
    if customer.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Customer status is '{customer.status}', cannot rollback stage.",
        )

    old_stage = customer.current_stage
    new_stage = old_stage - 1

    # Update customer
    customer.current_stage = new_stage
    customer.stage_entered_at = datetime.now(timezone.utc)

    # Record stage history
    history = StageHistory(
        customer_id=customer_id,
        from_stage=old_stage,
        to_stage=new_stage,
        changed_by=operator_id,
        remark=remark or f"Rolled back from stage {old_stage} to {new_stage}",
    )
    db.add(history)
    db.commit()
    db.refresh(customer)

    return customer
