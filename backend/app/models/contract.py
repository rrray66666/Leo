import uuid
from datetime import date, datetime

from sqlalchemy import Date, ForeignKey, Numeric, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin


class Contract(TimestampMixin, Base):
    __tablename__ = "contracts"

    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("customers.id"), nullable=False
    )
    contract_no: Mapped[str] = mapped_column(String(50), nullable=False)
    contract_amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=True)
    sign_date: Mapped[date] = mapped_column(Date, nullable=True)
    payment_terms: Mapped[str] = mapped_column(Text, nullable=True)
    delivery_date: Mapped[date] = mapped_column(Date, nullable=True)
    contract_file: Mapped[str] = mapped_column(String(500), nullable=True)

    # relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="contracts")

    def __repr__(self) -> str:
        return f"<Contract {self.contract_no}>"
