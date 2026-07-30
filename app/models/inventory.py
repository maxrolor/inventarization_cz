from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey, Text, JSON, Enum, Boolean
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base
import enum


class InventorySessionStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class DifferenceType(str, enum.Enum):
    MISSING = "missing"      # марка есть в ЧЗ, но не отсканирована
    EXTRA = "extra"          # марка отсканирована, но её нет в ЧЗ
    MISMATCH = "mismatch"    # статус не совпадает


class InventorySession(Base):
    __tablename__ = "inventory_sessions"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    status = Column(Enum(InventorySessionStatus), default=InventorySessionStatus.ACTIVE)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    total_scanned = Column(Integer, default=0)
    total_mismatches = Column(Integer, default=0)
    extra_data = Column(JSON, nullable=True)

    client = relationship("Client", back_populates="inventory_sessions")
    scanned_marks = relationship("ScannedMark", back_populates="session", cascade="all, delete-orphan")
    differences = relationship("InventoryDifference", back_populates="session", cascade="all, delete-orphan")
    write_off_documents = relationship("WriteOffDocument", back_populates="session", cascade="all, delete-orphan")


class ScannedMark(Base):
    __tablename__ = "scanned_marks"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("inventory_sessions.id"), nullable=False)
    mark_code = Column(String(255), nullable=False, index=True)
    product_name = Column(String(255), nullable=True)
    scanned_at = Column(DateTime(timezone=True), server_default=func.now())
    is_valid = Column(Boolean, default=True)
    validation_error = Column(Text, nullable=True)

    session = relationship("InventorySession", back_populates="scanned_marks")


class InventoryDifference(Base):
    __tablename__ = "inventory_differences"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("inventory_sessions.id"), nullable=False)
    mark_code = Column(String(255), nullable=False, index=True)
    expected_status = Column(String(50), nullable=True)
    actual_status = Column(String(50), nullable=True)
    difference_type = Column(Enum(DifferenceType), nullable=False)

    session = relationship("InventorySession", back_populates="differences")


class WriteOffDocument(Base):
    __tablename__ = "write_off_documents"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("inventory_sessions.id"), nullable=False)
    document_id = Column(String(100), nullable=True)
    status = Column(String(50), default="pending")
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    sent_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)

    session = relationship("InventorySession", back_populates="write_off_documents")