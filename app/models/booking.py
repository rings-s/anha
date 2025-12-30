import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class BookingStatus(str, enum.Enum):
    requested = "requested"
    assigned = "assigned"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    status: Mapped[BookingStatus] = mapped_column(Enum(BookingStatus), default=BookingStatus.requested)

    contact_name: Mapped[str] = mapped_column(String(255))
    contact_phone: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(Text, default="")
    location_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    address_text: Mapped[str] = mapped_column(String(255), default="")

    assigned_employee_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    client = relationship("User", back_populates="bookings", foreign_keys=[client_id])
    assigned_employee = relationship("User", back_populates="assigned_bookings", foreign_keys=[assigned_employee_id])
    service = relationship("Service", back_populates="bookings")
    review = relationship("Review", back_populates="booking", uselist=False)
