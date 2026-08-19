import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("admin", "sales", "pm", "cs", name="user_role"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # relationships
    customers: Mapped[list["Customer"]] = relationship(
        "Customer", back_populates="sales", foreign_keys="Customer.sales_id"
    )
    assigned_tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="assignee", foreign_keys="Task.assignee_id"
    )
    uploaded_documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="uploader", foreign_keys="Document.uploaded_by"
    )
    communications: Mapped[list["Communication"]] = relationship(
        "Communication", back_populates="user", foreign_keys="Communication.user_id"
    )
    recorded_payments: Mapped[list["Payment"]] = relationship(
        "Payment", back_populates="recorder", foreign_keys="Payment.recorded_by"
    )
    stage_changes: Mapped[list["StageHistory"]] = relationship(
        "StageHistory",
        back_populates="operator",
        foreign_keys="StageHistory.changed_by",
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user", foreign_keys="Notification.user_id"
    )
    follow_ups: Mapped[list["FollowUp"]] = relationship(
        "FollowUp", back_populates="user", foreign_keys="FollowUp.user_id"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="user", foreign_keys="AuditLog.user_id"
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"
