"""Issue database model."""
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .base import Base


class IssueRecord(Base):
    """Issue record with checklist."""
    __tablename__ = "issues"
    
    id = Column(Integer, primary_key=True, index=True)
    repo = Column(Text, nullable=False, index=True)
    issue_number = Column(Integer, nullable=False, index=True)
    checklist = Column(JSON, nullable=False)  # JSONB in PostgreSQL
    status = Column(String(50), default="open")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    pull_requests = relationship("PRRecord", back_populates="issue", lazy="selectin")
    
    class Config:
        """Pydantic config."""
        from_attributes = True

