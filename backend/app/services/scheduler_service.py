"""Background scheduler for automatic alerts and notifications"""
import logging
from datetime import date, datetime, timedelta, timezone

import redis as redis_lib
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.customer import Customer
from app.models.task import Task
from app.models.payment import Payment
from app.models.communication import Communication
from app.models.notification import Notification
from app.models.user import User

logger = logging.getLogger(__name__)

_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis_lib.from_url(settings.REDIS_URL)
        except Exception:
            _redis_client = None
    return _redis_client


def _acquire_lock(lock_name: str, timeout: int = 60) -> bool:
    """Try to acquire a distributed lock via Redis. Returns True if acquired."""
    r = _get_redis()
    if r is None:
        return True  # Redis unavailable, allow execution
    try:
        return bool(r.set(lock_name, "1", nx=True, ex=timeout))
    except Exception:
        return True


def _release_lock(lock_name: str):
    """Release a previously acquired distributed lock."""
    try:
        r = _get_redis()
        if r:
            r.delete(lock_name)
    except Exception:
        pass


def check_lead_timeout():
    """
    Automatically mark leads in stage 1 with no communication for >30 days as lost.
    Section 7.1: 线索超时：①阶段 > 30天无沟通 → 自动标记流失
    """
    if not _acquire_lock("scheduler:lead_timeout", timeout=3600):
        return
    db: Session = SessionLocal()
    try:
        # MySQL DATETIME columns come back naive; compare with a naive cutoff
        # so offset-naive vs offset-aware comparisons never raise TypeError.
        thirty_days_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)

        # Find active customers in stage 1
        leads = (
            db.query(Customer)
            .filter(
                Customer.current_stage == 1,
                Customer.status == "active",
            )
            .all()
        )

        marked_count = 0
        for lead in leads:
            # Check latest communication
            latest_comm = (
                db.query(Communication)
                .filter(Communication.customer_id == lead.id)
                .order_by(Communication.created_at.desc())
                .first()
            )

            should_mark_lost = False
            if not latest_comm:
                # No communication ever - check if created > 30 days ago
                if lead.created_at and lead.created_at < thirty_days_ago:
                    should_mark_lost = True
            else:
                # Has communication - check if last one was > 30 days ago
                if latest_comm.created_at and latest_comm.created_at < thirty_days_ago:
                    should_mark_lost = True

            if should_mark_lost:
                lead.status = "lost"
                lead.lost_reason = "Auto-marked: No communication for over 30 days in Lead stage"

                # Create notification for sales person
                if lead.sales_id:
                    notification = Notification(
                        user_id=lead.sales_id,
                        type="auto_lost",
                        title="Lead auto-marked as lost",
                        content=f"Customer '{lead.name}' has been automatically marked as lost due to no communication for over 30 days in the Lead stage.",
                        related_id=lead.id,
                        related_type="customer",
                    )
                    db.add(notification)

                marked_count += 1

        db.commit()
        if marked_count > 0:
            logger.info(f"Scheduler: Marked {marked_count} leads as lost (timeout)")
    except Exception as e:
        db.rollback()
        logger.error(f"Scheduler error (lead_timeout): {e}")
    finally:
        db.close()
        _release_lock("scheduler:lead_timeout")


def check_task_due():
    """
    Push notifications for tasks due today.
    Section 7.1: 任务到期：due_date = 今天 → 推送待办
    """
    if not _acquire_lock("scheduler:task_due", timeout=3600):
        return
    db: Session = SessionLocal()
    try:
        today = date.today()

        due_tasks = (
            db.query(Task)
            .filter(
                Task.due_date == today,
                Task.status.in_(["pending", "in_progress"]),
            )
            .all()
        )

        count = 0
        for task in due_tasks:
            if task.assignee_id:
                notification = Notification(
                    user_id=task.assignee_id,
                    type="task_due",
                    title="Task due today",
                    content=f"Task '{task.name}' is due today. Please complete it on time.",
                    related_id=task.id,
                    related_type="task",
                )
                db.add(notification)
                count += 1

        db.commit()
        if count > 0:
            logger.info(f"Scheduler: Created {count} task-due notifications")
    except Exception as e:
        db.rollback()
        logger.error(f"Scheduler error (task_due): {e}")
    finally:
        db.close()
        _release_lock("scheduler:task_due")


def check_payment_overdue():
    """
    Notify for overdue payments.
    Section 7.1: 回款逾期：超过约定日期 → 通知财务和销售

    Since payments table doesn't have a 'due_date' field, we check:
    - Customers who have a contract_amount > 0
    - But paid_amount < contract_amount
    - And have been in stage 7 (回款) for more than 30 days
    """
    if not _acquire_lock("scheduler:payment_overdue", timeout=3600):
        return
    db: Session = SessionLocal()
    try:
        thirty_days_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)

        overdue_customers = (
            db.query(Customer)
            .filter(
                Customer.current_stage == 7,
                Customer.status == "active",
                Customer.stage_entered_at < thirty_days_ago,
                Customer.contract_amount > Customer.paid_amount,
            )
            .all()
        )

        count = 0
        for c in overdue_customers:
            unpaid = float(c.contract_amount - c.paid_amount)

            # Notify sales person
            if c.sales_id:
                notification = Notification(
                    user_id=c.sales_id,
                    type="payment_overdue",
                    title="Payment overdue",
                    content=f"Customer '{c.name}' has an overdue payment of {unpaid:.2f}. Please follow up.",
                    related_id=c.id,
                    related_type="customer",
                )
                db.add(notification)
                count += 1

            # Also notify admin users
            admins = db.query(User).filter(User.role == "admin", User.is_active == True).all()
            for admin in admins:
                existing = (
                    db.query(Notification)
                    .filter(
                        Notification.user_id == admin.id,
                        Notification.type == "payment_overdue",
                        Notification.related_id == c.id,
                        func.date(Notification.created_at) == date.today(),
                    )
                    .first()
                )
                if not existing:
                    notification = Notification(
                        user_id=admin.id,
                        type="payment_overdue",
                        title="Payment overdue alert",
                        content=f"Customer '{c.name}' has an overdue payment of {unpaid:.2f}.",
                        related_id=c.id,
                        related_type="customer",
                    )
                    db.add(notification)
                    count += 1

        db.commit()
        if count > 0:
            logger.info(f"Scheduler: Created {count} payment-overdue notifications")
    except Exception as e:
        db.rollback()
        logger.error(f"Scheduler error (payment_overdue): {e}")
    finally:
        db.close()
        _release_lock("scheduler:payment_overdue")
