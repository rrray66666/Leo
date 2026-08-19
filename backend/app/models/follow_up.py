import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class FollowUp(TimestampMixin, Base):
    __tablename__ = "follow_ups"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    remind_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    remind_type: Mapped[str] = mapped_column(
        Enum("system_notification", "email", "high_priority", name="remind_type"),
        default="system_notification",
        nullable=False,
    )
    is_done: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    done_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    # relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="follow_ups")
    user: Mapped["User"] = relationship("User", back_populates="follow_ups", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<FollowUp {self.title}>"
