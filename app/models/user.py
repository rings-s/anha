import enum
from datetime import datetime

from sqlalchemy import DateTime, String, Boolean, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class Role(str, enum.Enum):
    client = "client"
    employee = "employee"
    driver = "driver"
    technical = "technical"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(50), default="")
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.client)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    bookings = relationship("Booking", back_populates="client", foreign_keys="Booking.client_id")
    assigned_bookings = relationship(
        "Booking", back_populates="assigned_employee", foreign_keys="Booking.assigned_employee_id"
    )
