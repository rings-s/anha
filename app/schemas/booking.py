from datetime import datetime
from pydantic import BaseModel, Field


class BookingCreate(BaseModel):
    service_id: int
    contact_name: str
    contact_phone: str
    description: str = ""
    location_lat: float | None = None
    location_lng: float | None = None
    address_text: str = ""


class BookingOut(BaseModel):
    id: int
    service_id: int
    status: str
    contact_name: str
    contact_phone: str
    description: str
    location_lat: float | None
    location_lng: float | None
    address_text: str
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = ""
