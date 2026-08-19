import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=True)
    payment_type: Mapped[str] = mapped_column(
        Enum("deposit", "milestone", "final", name="payment_type"),
        nullable=False,
    )
    invoice_no: Mapped[str] = mapped_column(String(50), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    recorded_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="payments")
    recorder: Mapped["User"] = relationship("User", back_populates="recorded_payments", foreign_keys=[recorded_by])

    def __repr__(self) -> str:
        return f"<Payment {self.id}>"
