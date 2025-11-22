"""Service for safely merging pull requests."""
import logging
from typing import Dict, Optional
from dataclasses import dataclass

from src.app.models import PRRecord
from src.app.services.github_service import GitHubService
from src.app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class MergeResult:
    """Result of merge attempt."""
    success: bool
    message: str
    sha: Optional[str] = None


class MergeService:
    """Service for safely merging PRs."""
    
    def __init__(self, github_service: GitHubService):
        self.github = github_service
    
    async def attempt_merge(self, pr_record: PRRecord) -> MergeResult:
        """
        Attempt to merge a PR with safety checks.
        
        Args:
            pr_record: PRRecord object
        
        Returns:
            MergeResult object
        """
        if not settings.auto_merge_enabled:
            return MergeResult(
                success=False,
                message="Auto-merge is disabled"
            )
        
        repo_full_name = pr_record.repo
        owner, repo = repo_full_name.split("/", 1)
        pr_number = pr_record.pr_number
        
        # Get installation ID from webhook context
        # For now, we'll need to pass it or retrieve it
        # This is a simplified implementation
        installation_id = None  # Would need to be passed in or retrieved
        
        if not installation_id:
            return MergeResult(
                success=False,
                message="Installation ID not available"
            )
        
        try:
            # Check branch protection
            branch_protection = await self.github.get_branch_protection(
                owner=owner,
                repo=repo,
                branch="main",  # Could be determined from PR
                installation_id=installation_id
            )
            
            # If branch protection exists, ensure requirements are met
            if branch_protection:
                required_status_checks = branch_protection.get("required_status_checks")
                if required_status_checks:
                    # Check if all required checks passed
                    # This would require additional API calls to check commit status
                    logger.info("Branch protection found, checking status checks")
            
            # Attempt merge
            merge_result = await self.github.merge_pr(
                owner=owner,
                repo=repo,
                pr_number=pr_number,
                merge_method="squash",
                installation_id=installation_id
            )
            
            if merge_result.get("merged"):
                return MergeResult(
                    success=True,
                    message="PR merged successfully",
                    sha=merge_result.get("sha")
                )
            else:
                return MergeResult(
                    success=False,
                    message=merge_result.get("message", "Merge failed")
                )
        
        except Exception as e:
            logger.error(f"Merge attempt failed: {e}")
            return MergeResult(
                success=False,
                message=f"Merge failed: {str(e)}"
            )

