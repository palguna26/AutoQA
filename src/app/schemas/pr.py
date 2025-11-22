"""Pydantic schemas for pull requests."""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class TestManifestEntry(BaseModel):
    """A single test manifest entry."""
    test_id: str = Field(..., description="Unique test identifier")
    name: str = Field(..., description="Test name")
    framework: str = Field(default="pytest", description="Test framework")
    target: str = Field(..., description="Target file path")
    checklist: List[str] = Field(default_factory=list, description="Associated checklist IDs")


class TestManifest(BaseModel):
    """Test manifest for a PR."""
    pr_number: int
    head_sha: str
    tests: List[TestManifestEntry]


class PRCreate(BaseModel):
    """Schema for creating a PR record."""
    repo: str
    pr_number: int
    issue_id: Optional[int] = None
    head_sha: Optional[str] = None
    test_manifest: Optional[TestManifest] = None


class PRResponse(BaseModel):
    """Schema for PR record response."""
    id: int
    repo: str
    pr_number: int
    issue_id: Optional[int]
    head_sha: Optional[str]
    test_manifest: Optional[dict]
    validation_status: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

