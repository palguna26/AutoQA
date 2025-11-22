"""Pydantic schemas for issues."""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class ChecklistItem(BaseModel):
    """A single checklist item."""
    id: str = Field(..., description="Unique identifier (e.g., C1, C2)")
    description: str = Field(..., description="Description of the requirement")
    required: bool = Field(default=True, description="Whether this item is required")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    
    class Config:
        from_attributes = True


class IssueCreate(BaseModel):
    """Schema for creating an issue record."""
    repo: str
    issue_number: int
    checklist: List[ChecklistItem]


class IssueResponse(BaseModel):
    """Schema for issue record response."""
    id: int
    repo: str
    issue_number: int
    checklist: List[ChecklistItem]
    status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

