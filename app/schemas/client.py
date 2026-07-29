from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime, date
from app.models.client import ClientType

class ClientBase(BaseModel):
    inn: str = Field(..., min_length=10, max_length=12)
    name: str
    ceo_name: Optional[str] = None
    type: ClientType = ClientType.LEGAL
    kpp: Optional[str] = Field(None, min_length=9, max_length=9)
    phone: Optional[str] = None
    email: Optional[str] = None  # изменено с EmailStr на str для поддержки любых доменов
    subscription_end_date: Optional[date] = None

    @field_validator('inn')
    def validate_inn(cls, v):
        if not v.isdigit():
            raise ValueError('ИНН должен содержать только цифры')
        if len(v) not in [10, 12]:
            raise ValueError('ИНН должен быть 10 или 12 цифр')
        return v

class ClientCreate(ClientBase):
    password: str = Field(..., min_length=6)
    addresses: List[str] = Field(default_factory=list)

class ClientUpdate(BaseModel):
    name: Optional[str] = None
    ceo_name: Optional[str] = None
    type: Optional[ClientType] = None
    kpp: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    subscription_end_date: Optional[date] = None
    addresses: Optional[List[str]] = None

class ClientResponse(ClientBase):
    id: int
    is_verified: bool
    is_blocked: bool
    created_at: datetime
    updated_at: datetime
    addresses: List[str] = []
    email_confirmed: Optional[bool] = None

    class Config:
        from_attributes = True

class ClientLogin(BaseModel):
    inn: str
    password: str