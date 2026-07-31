from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, Text, JSON, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class ClientType(str, enum.Enum):
    INDIVIDUAL = "individual"
    LEGAL = "legal"


class CzEnvironment(str, enum.Enum):
    """Окружение Честного знака: песочница или боевой контур."""
    SANDBOX = "sandbox"
    PRODUCTION = "production"


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    inn = Column(String(12), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=True)                 # название компании
    ceo_name = Column(String(255), nullable=True)             # ФИО руководителя
    type = Column(Enum(ClientType), nullable=True, default=ClientType.INDIVIDUAL)
    kpp = Column(String(20), nullable=True)                   # КПП для юрлиц
    email = Column(String(255), index=True, nullable=False)
    phone = Column(String(20), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)              # подтверждён ли клиент админом
    is_blocked = Column(Boolean, default=False)
    email_confirmed = Column(Boolean, default=False)          # подтверждён ли email
    confirmation_token = Column(String(255), nullable=True)   # токен для подтверждения email
    subscription_end_date = Column(Date, nullable=True)       # дата окончания подписки
    created_at = Column(DateTime(timezone=True), server_default=func.now(), default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Поля для интеграции с Честным знаком
    cz_environment = Column(Enum(CzEnvironment), default=CzEnvironment.SANDBOX)
    cz_token_encrypted = Column(Text, nullable=True)
    cz_token_expires = Column(DateTime, nullable=True)
    cz_api_url = Column(String(255), nullable=True)

    # Связи с другими моделями
    users = relationship("User", back_populates="client", cascade="all, delete-orphan")
    addresses = relationship("ClientAddress", back_populates="client", cascade="all, delete-orphan")
    inventory_sessions = relationship(
        "InventorySession",
        back_populates="client",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Client(id={self.id}, inn={self.inn}, email={self.email})>"