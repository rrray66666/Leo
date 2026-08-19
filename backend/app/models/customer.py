import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    contact_person: Mapped[str] = mapped_column(String(50), nullable=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    wechat: Mapped[str] = mapped_column(String(50), nullable=True)
    email: Mapped[str] = mapped_column(String(100), nullable=True)
    company: Mapped[str] = mapped_column(String(200), nullable=True)
    region: Mapped[str] = mapped_column(String(50), nullable=True)
    source_channel: Mapped[str] = mapped_column(String(50), nullable=True)
    sales_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    current_stage: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    stage_entered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    contract_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    paid_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    status: Mapped[str] = mapped_column(
        Enum("active", "lost", "completed", "terminated", "deleted", name="customer_status"),
        default="active",
        nullable=False,
    )
    lost_reason: Mapped[str] = mapped_column(Text, nullable=True)

    # relationships
    sales: Mapped["User"] = relationship("User", back_populates="customers", foreign_keys=[sales_id])
    contracts: Mapped[list["Contract"]] = relationship(
        "Contract", back_populates="customer", cascade="all, delete-orphan"
    )
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="customer", cascade="all, delete-orphan"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="customer", cascade="all, delete-orphan"
    )
    communications: Mapped[list["Communication"]] = relationship(
        "Communication", back_populates="customer", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(
        "Payment", back_populates="customer", cascade="all, delete-orphan"
    )
    stage_histories: Mapped[list["StageHistory"]] = relationship(
        "StageHistory", back_populates="customer", cascade="all, delete-orphan"
    )
    follow_ups: Mapped[list["FollowUp"]] = relationship(
        "FollowUp", back_populates="customer", cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="customer", foreign_keys="AuditLog.customer_id", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Customer {self.name}>"
