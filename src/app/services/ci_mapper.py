"""Service for mapping CI results to checklists and generating reports."""
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

from src.app.models import PRRecord, TestResult, Report
from src.app.adapters.db_adapter import DBAdapter
from src.app.services.github_service import GitHubService
from src.app.utils.junit_parser import parse_junit, TestResultModel
from src.app.config import settings
from src.app.services.merge_service import MergeService

logger = logging.getLogger(__name__)


@dataclass
class ReportResult:
    """Result of report generation."""
    pr_id: int
    compliance_score: float
    required_passed: int
    required_total: int
    report_id: Optional[int] = None


class CIMapper:
    """Service for mapping CI results to checklists."""
    
    def __init__(
        self,
        db_adapter: DBAdapter,
        github_service: GitHubService,
        merge_service: MergeService
    ):
        self.db = db_adapter
        self.github = github_service
        self.merge_service = merge_service
    
    async def handle_workflow_run(self, event: Dict) -> ReportResult:
        """
        Handle GitHub workflow_run completed event.
        
        Args:
            event: GitHub webhook event payload
        
        Returns:
            ReportResult object
        """
        workflow_run = event.get("workflow_run", {})
        repo_data = event.get("repository", {})
        action = event.get("action")
        
        # Only process completed workflow runs
        if action != "completed":
            logger.info(f"Skipping workflow_run event with action: {action}")
            raise ValueError(f"Unexpected workflow_run action: {action}")
        
        run_id = workflow_run.get("id")
        head_sha = workflow_run.get("head_sha")
        repo_full_name = repo_data.get("full_name")
        installation_id = event.get("installation", {}).get("id")
        
        if not all([run_id, head_sha, repo_full_name, installation_id]):
            raise ValueError("Missing required fields in workflow_run event")
        
        # Find PR by head_sha
        # This is a simplified lookup - in production you might want a better mapping
        pr_record = await self._find_pr_by_sha(repo_full_name, head_sha)
        
        if not pr_record:
            logger.warning(f"No PR found for SHA {head_sha} in {repo_full_name}")
            raise ValueError(f"PR not found for SHA {head_sha}")
        
        owner, repo = repo_full_name.split("/", 1)
        
        # Download and parse test artifacts
        test_results = await self._download_and_parse_artifacts(
            owner=owner,
            repo=repo,
            run_id=run_id,
            installation_id=installation_id
        )
        
        # Map test results to checklist
        compliance = await self._map_results_to_checklist(pr_record, test_results)
        
        # Generate and save report
        report = await self._generate_report(pr_record, compliance, test_results)
        
        # Post PR comment
        comment_body = self._format_report_comment(compliance, test_results)
        
        try:
            await self.github.post_pr_comment(
                owner=owner,
                repo=repo,
                pr_number=pr_record.pr_number,
                body=comment_body,
                installation_id=installation_id
            )
        except Exception as e:
            logger.error(f"Failed to post PR comment: {e}")
        
        # Check if auto-merge is enabled and all required items passed
        if settings.auto_merge_enabled and compliance["required_passed"] == compliance["required_total"]:
            try:
                await self.merge_service.attempt_merge(pr_record)
            except Exception as e:
                logger.error(f"Auto-merge failed: {e}")
        
        return ReportResult(
            pr_id=pr_record.id,
            compliance_score=compliance["score"],
            required_passed=compliance["required_passed"],
            required_total=compliance["required_total"],
            report_id=report.id if report else None
        )
    
    async def _find_pr_by_sha(self, repo: str, head_sha: str) -> Optional[PRRecord]:
        """Find PR record by head SHA."""
        from sqlalchemy import select
        from src.app.models import PRRecord
        
        result = await self.db.session.execute(
            select(PRRecord)
            .where(PRRecord.repo == repo)
            .where(PRRecord.head_sha == head_sha)
            .order_by(PRRecord.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def _download_and_parse_artifacts(
        self,
        owner: str,
        repo: str,
        run_id: int,
        installation_id: int
    ) -> List[TestResultModel]:
        """Download and parse JUnit XML artifacts."""
        # List artifacts
        artifacts = await self.github.list_workflow_run_artifacts(
            owner=owner,
            repo=repo,
            run_id=run_id,
            installation_id=installation_id
        )
        
        test_results = []
        
        # Look for autoqa test report artifact
        for artifact in artifacts:
            artifact_name = artifact.get("name", "")
            
            # Look for autoqa test report
            if "autoqa" in artifact_name.lower() or "test-report" in artifact_name.lower():
                artifact_id = artifact.get("id")
                
                try:
                    # Download artifact
                    artifact_bytes = await self.github.download_artifact(
                        owner=owner,
                        repo=repo,
                        artifact_id=artifact_id,
                        installation_id=installation_id
                    )
                    
                    # Extract and parse JUnit XML
                    # Note: artifact_bytes is a zip file, needs extraction
                    # For now, assume the XML is directly in the zip
                    # In production, use zipfile to extract
                    import zipfile
                    import io
                    
                    with zipfile.ZipFile(io.BytesIO(artifact_bytes)) as zip_file:
                        # Look for JUnit XML file
                        for file_name in zip_file.namelist():
                            if file_name.endswith(".xml"):
                                xml_content = zip_file.read(file_name)
                                parsed_results = parse_junit(xml_content)
                                test_results.extend(parsed_results)
                                break
                except Exception as e:
                    logger.error(f"Failed to parse artifact {artifact_name}: {e}")
        
        return test_results
    
    async def _map_results_to_checklist(
        self,
        pr_record: PRRecord,
        test_results: List[TestResultModel]
    ) -> Dict:
        """Map test results to checklist items."""
        # Get checklist from linked issue
        from src.app.models import IssueRecord
        from src.app.schemas.issue import ChecklistItem
        
        checklist_items = []
        if pr_record.issue_id:
            issue_record = await self.db.session.get(IssueRecord, pr_record.issue_id)
            if issue_record:
                checklist_items = [
                    ChecklistItem(**item) if isinstance(item, dict) else item
                    for item in issue_record.checklist
                ]
        
        # Get test manifest
        manifest = pr_record.test_manifest or {}
        manifest_tests = manifest.get("tests", [])
        
        # Map test results to checklist
        required_total = sum(1 for item in checklist_items if item.required)
        required_passed = 0
        
        # Save test results to DB
        db_test_results = []
        
        for test_result in test_results:
            # Find matching manifest entry
            manifest_entry = None
            for entry in manifest_tests:
                if entry.get("name") == test_result.name:
                    manifest_entry = entry
                    break
            
            # Get associated checklist IDs
            checklist_ids = manifest_entry.get("checklist", []) if manifest_entry else []
            
            # If no explicit mapping, try fuzzy matching
            if not checklist_ids:
                checklist_ids = self._fuzzy_match_checklist(test_result.name, checklist_items)
            
            # Determine if this test covers required items
            covers_required = any(
                item.id in checklist_ids and item.required
                for item in checklist_items
            )
            
            if covers_required and test_result.status == "passed":
                required_passed += 1
            
            # Save test result
            db_result = TestResult(
                pr_id=pr_record.id,
                test_id=manifest_entry.get("test_id") if manifest_entry else None,
                name=test_result.name,
                status=test_result.status,
                checklist_ids=checklist_ids,
                log_url=None  # Could be extracted from artifact
            )
            db_test_results.append(db_result)
        
        # Save test results
        await self.db.save_test_results(db_test_results)
        
        # Calculate compliance score
        score = required_passed / required_total if required_total > 0 else 0.0
        
        return {
            "score": score,
            "required_passed": required_passed,
            "required_total": required_total,
            "total_tests": len(test_results),
            "passed_tests": sum(1 for t in test_results if t.status == "passed")
        }
    
    def _fuzzy_match_checklist(self, test_name: str, checklist_items: List) -> List[str]:
        """Fuzzy match test name to checklist items."""
        from src.app.schemas.issue import ChecklistItem
        
        checklist_ids = []
        test_lower = test_name.lower()
        
        for item in checklist_items:
            # Ensure item is a ChecklistItem object
            if isinstance(item, dict):
                item = ChecklistItem(**item)
            
            item_lower = item.description.lower()
            
            # Extract keywords from test name
            test_words = set(test_lower.replace("test_", "").replace("_", " ").split())
            
            # Extract keywords from checklist description
            item_words = set()
            for word in item_lower.split():
                if word not in ["the", "a", "an", "for", "and", "or", "but", "to", "of", "in", "on", "at"]:
                    item_words.add(word.strip(".,!?;:"))
            
            # Check for keyword overlap
            if test_words & item_words and len(test_words & item_words) >= 2:
                checklist_ids.append(item.id)
        
        return checklist_ids
    
    async def _generate_report(
        self,
        pr_record: PRRecord,
        compliance: Dict,
        test_results: List[TestResultModel]
    ) -> Report:
        """Generate report from compliance and test results."""
        summary = f"Compliance Score: {compliance['score']:.0%} ({compliance['required_passed']}/{compliance['required_total']} required items passed)"
        
        report_content = f"""# AutoQA Review Report

## Summary
{summary}

## Test Results
- Total Tests: {compliance['total_tests']}
- Passed: {compliance['passed_tests']}
- Failed: {compliance['total_tests'] - compliance['passed_tests']}

## Compliance
- Required Items Passed: {compliance['required_passed']}/{compliance['required_total']}
- Compliance Score: {compliance['score']:.0%}

## Status
{"✅ All required items passed" if compliance['required_passed'] == compliance['required_total'] else "⚠️ Some required items failed"}
"""
        
        report = Report(
            pr_id=pr_record.id,
            report_content=report_content,
            summary=summary
        )
        
        return await self.db.save_report(report)
    
    def _format_report_comment(self, compliance: Dict, test_results: List[TestResultModel]) -> str:
        """Format report as GitHub PR comment."""
        comment = "## 📋 AutoQA Review Report\n\n"
        
        comment += f"**Compliance Score:** {compliance['score']:.0%}\n\n"
        comment += f"✅ **Required Items Passed:** {compliance['required_passed']}/{compliance['required_total']}\n\n"
        
        comment += "### Test Results\n\n"
        comment += f"- Total Tests: {compliance['total_tests']}\n"
        comment += f"- Passed: {compliance['passed_tests']}\n"
        comment += f"- Failed: {compliance['total_tests'] - compliance['passed_tests']}\n\n"
        
        if compliance['required_passed'] == compliance['required_total']:
            comment += "✅ **All required checklist items passed!**\n"
        else:
            comment += f"⚠️ **{compliance['required_total'] - compliance['required_passed']} required items still need attention.**\n"
        
        return comment

