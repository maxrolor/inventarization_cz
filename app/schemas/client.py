from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, date
from app.models.client import ClientType, CzEnvironment


# ---------- Базовые схемы ----------
class ClientBase(BaseModel):
    inn: str = Field(..., min_length=10, max_length=12)
    name: Optional[str] = None
    ceo_name: Optional[str] = None
    type: Optional[ClientType] = ClientType.INDIVIDUAL
    kpp: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    is_blocked: bool = False
    cz_environment: CzEnvironment = CzEnvironment.SANDBOX
    cz_token: Optional[str] = None
    cz_api_url: Optional[str] = None
    addresses: List[str] = []


class ClientCreate(ClientBase):
    password: str = Field(..., min_length=6)


class ClientLogin(BaseModel):
    inn: str
    password: str


class ClientUpdate(BaseModel):
    inn: Optional[str] = Field(None, min_length=10, max_length=12)
    name: Optional[str] = None
    ceo_name: Optional[str] = None
    type: Optional[ClientType] = None
    kpp: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    is_blocked: Optional[bool] = None
    cz_environment: Optional[CzEnvironment] = None
    cz_token: Optional[str] = None
    cz_api_url: Optional[str] = None
    addresses: Optional[List[str]] = None


class ClientResponse(ClientBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True