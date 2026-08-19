import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Communication(TimestampMixin, Base):
    __tablename__ = "communications"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    channel: Mapped[str] = mapped_column(
        Enum("phone", "wechat", "meeting", "email", name="comm_channel"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=True)
    next_action: Mapped[str] = mapped_column(Text, nullable=True)
    next_action_date: Mapped[date] = mapped_column(Date, nullable=True)

    # relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="communications")
    user: Mapped["User"] = relationship("User", back_populates="communications", foreign_keys=[user_id])

    def __repr__(self) -> str:
        return f"<Communication {self.id}>"
