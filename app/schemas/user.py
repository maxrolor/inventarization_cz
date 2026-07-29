from pydantic import BaseModel, EmailStr
from typing import Optional
from app.models.user import UserRole

class UserLogin(BaseModel):
    username: str
    password: str

class UserRegister(BaseModel):
    username: str
    password: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: UserRole = UserRole.CLIENT

class UserUpdate(BaseModel):
    """Обновление пользователя"""
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    role: UserRole
    is_active: bool
    client_id: Optional[int]

    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    """Список пользователей (без паролей)"""
    id: int
    username: str
    email: Optional[str]
    phone: Optional[str]
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    created_at: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

# ИСПРАВЛЕНО: используем str вместо EmailStr для восстановления пароля
class ResetPasswordRequest(BaseModel):
    email: str  # <-- было EmailStr

class ResetPasswordVerify(BaseModel):
    email: str  # <-- было EmailStr
    code: str
    new_password: str





    class Config:
        from_attributes = True