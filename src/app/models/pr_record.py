"""Pull Request database model."""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class PRRecord(Base):
    """Pull request record with test manifest."""
    __tablename__ = "pull_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    repo = Column(Text, nullable=False, index=True)
    pr_number = Column(Integer, nullable=False, index=True)
    issue_id = Column(Integer, ForeignKey("issues.id"), nullable=True)
    head_sha = Column(String(40))
    test_manifest = Column(JSON)  # JSONB in PostgreSQL
    validation_status = Column(String(50), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    issue = relationship("IssueRecord", back_populates="pull_requests", lazy="selectin")
    test_results = relationship("TestResult", back_populates="pr", cascade="all, delete-orphan", lazy="selectin")
    reports = relationship("Report", back_populates="pr", cascade="all, delete-orphan", lazy="selectin")
    
    class Config:
        """Pydantic config."""
        from_attributes = True

