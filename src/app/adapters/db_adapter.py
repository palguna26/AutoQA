"""Database adapter for CRUD operations."""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from src.app.models import IssueRecord, PRRecord, TestResult, Report
from src.app.schemas.issue import ChecklistItem


class DBAdapter:
    """Database operations adapter."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save_issue(self, issue_record: IssueRecord) -> IssueRecord:
        """Save or update an issue record."""
        self.session.add(issue_record)
        await self.session.commit()
        await self.session.refresh(issue_record)
        return issue_record
    
    async def get_issue_by_repo_and_number(self, repo: str, issue_number: int) -> Optional[IssueRecord]:
        """Get issue record by repository and issue number."""
        result = await self.session.execute(
            select(IssueRecord).where(
                and_(
                    IssueRecord.repo == repo,
                    IssueRecord.issue_number == issue_number
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def save_pr(self, pr_record: PRRecord) -> PRRecord:
        """Save or update a PR record."""
        self.session.add(pr_record)
        await self.session.commit()
        await self.session.refresh(pr_record)
        return pr_record
    
    async def get_pr_by_repo_and_number(self, repo: str, pr_number: int) -> Optional[PRRecord]:
        """Get PR record by repository and PR number."""
        result = await self.session.execute(
            select(PRRecord).where(
                and_(
                    PRRecord.repo == repo,
                    PRRecord.pr_number == pr_number
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def save_test_results(self, test_results: List[TestResult]) -> List[TestResult]:
        """Save multiple test results."""
        for result in test_results:
            self.session.add(result)
        await self.session.commit()
        for result in test_results:
            await self.session.refresh(result)
        return test_results
    
    async def save_report(self, report: Report) -> Report:
        """Save a report."""
        self.session.add(report)
        await self.session.commit()
        await self.session.refresh(report)
        return report
    
    async def get_latest_report_for_pr(self, pr_id: int) -> Optional[Report]:
        """Get the latest report for a PR."""
        result = await self.session.execute(
            select(Report)
            .where(Report.pr_id == pr_id)
            .order_by(Report.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

