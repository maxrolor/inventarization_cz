from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class MarkAvailable(Base):
    __tablename__ = "marks_available"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"))
    serial_number = Column(String, unique=True, index=True)
    status = Column(String, default="available")  # available, used, expired
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    client = relationship("Client")
