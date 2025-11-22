"""Pydantic schemas for reports."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ReportCreate(BaseModel):
    """Schema for creating a report."""
    pr_id: int
    report_content: str
    summary: Optional[str] = None


class ReportResponse(BaseModel):
    """Schema for report response."""
    id: int
    pr_id: int
    report_content: str
    summary: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

