import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class StageHistory(TimestampMixin, Base):
    __tablename__ = "stage_histories"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    from_stage: Mapped[int] = mapped_column(Integer, nullable=True)
    to_stage: Mapped[int] = mapped_column(Integer, nullable=False)
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    remark: Mapped[str] = mapped_column(Text, nullable=True)

    # relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="stage_histories")
    operator: Mapped["User"] = relationship("User", back_populates="stage_changes", foreign_keys=[changed_by])

    def __repr__(self) -> str:
        return f"<StageHistory {self.from_stage}->{self.to_stage}>"
