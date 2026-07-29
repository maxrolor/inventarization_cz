from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
import enum

class ClientType(str, enum.Enum):
    LEGAL = "legal"
    INDIVIDUAL = "individual"

class CzEnvironment(str, enum.Enum):
    SANDBOX = "sandbox"
    PRODUCTION = "production"

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    inn = Column(String(12), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    ceo_name = Column(String(255), nullable=True)
    type = Column(Enum(ClientType), nullable=False, default=ClientType.LEGAL)
    kpp = Column(String(9), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    is_verified = Column(Boolean, default=False)
    is_blocked = Column(Boolean, default=False)
    subscription_end_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Новые поля для Честного ЗНАКа
    cz_environment = Column(Enum(CzEnvironment), default=CzEnvironment.SANDBOX, nullable=False)
    cz_token = Column(String(500), nullable=True)          # Аутентификационный токен
    cz_api_url = Column(String(255), nullable=True)        # Можно переопределить URL

    email_confirmed = Column(Boolean, default=False)
    confirmation_token = Column(String(64), unique=True, nullable=True)

    user = relationship("User", back_populates="client", uselist=False)
    addresses = relationship("ClientAddress", back_populates="client", cascade="all, delete-orphan")