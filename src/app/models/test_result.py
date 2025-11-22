"""Test result and report database models."""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class TestResult(Base):
    """Test result record."""
    __tablename__ = "test_results"
    
    id = Column(Integer, primary_key=True, index=True)
    pr_id = Column(Integer, ForeignKey("pull_requests.id"), nullable=False)
    test_id = Column(String(100))
    name = Column(Text, nullable=False)
    status = Column(String(20), nullable=False)  # passed, failed, skipped
    log_url = Column(Text)
    checklist_ids = Column(JSON)  # List of checklist item IDs
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    pr = relationship("PRRecord", back_populates="test_results", lazy="selectin")
    
    class Config:
        """Pydantic config."""
        from_attributes = True


class Report(Base):
    """Report record for PR review."""
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    pr_id = Column(Integer, ForeignKey("pull_requests.id"), nullable=False)
    report_content = Column(Text, nullable=False)
    summary = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    pr = relationship("PRRecord", back_populates="reports", lazy="selectin")
    
    class Config:
        """Pydantic config."""
        from_attributes = True

