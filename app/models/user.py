from sqlalchemy import Column, Integer, String, Boolean, Enum, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum
import datetime

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    CLIENT = "CLIENT"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), index=True, nullable=True)
    phone = Column(String(20), nullable=True)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.CLIENT, nullable=False)
    is_active = Column(Boolean, default=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)

    client = relationship("Client", back_populates="users", uselist=False)