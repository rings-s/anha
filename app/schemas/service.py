from pydantic import BaseModel


class ServiceOut(BaseModel):
    id: int
    name_ar: str
    description_ar: str

    class Config:
        from_attributes = True
