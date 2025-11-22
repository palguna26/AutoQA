"""Service for generating test manifests from PRs."""
import logging
from typing import Dict, List, Optional

from src.app.models import PRRecord, IssueRecord
from src.app.schemas.pr import TestManifest, TestManifestEntry
from src.app.adapters.db_adapter import DBAdapter
from src.app.services.github_service import GitHubService
from src.app.utils.parser import find_linked_issue
from src.app.utils.diff_utils import extract_changed_symbols, get_changed_file_types

logger = logging.getLogger(__name__)


class TestGenService:
    """Service for generating test manifests from PRs."""
    
    def __init__(self, db_adapter: DBAdapter, github_service: GitHubService):
        self.db = db_adapter
        self.github = github_service
    
    async def handle_pr_event(self, event: Dict) -> PRRecord:
        """
        Handle GitHub pull request opened/synchronize event.
        
        Args:
            event: GitHub webhook event payload
        
        Returns:
            PRRecord object
        """
        pr_data = event.get("pull_request", {})
        repo_data = event.get("repository", {})
        action = event.get("action")  # opened, synchronize, etc.
        
        pr_number = pr_data.get("number")
        head_sha = pr_data.get("head", {}).get("sha")
        pr_body = pr_data.get("body", "")
        pr_title = pr_data.get("title", "")
        branch_name = pr_data.get("head", {}).get("ref")
        repo_full_name = repo_data.get("full_name")
        installation_id = event.get("installation", {}).get("id")
        
        if not all([pr_number, head_sha, repo_full_name, installation_id]):
            raise ValueError("Missing required fields in PR event")
        
        logger.info(f"Processing PR #{pr_number} in {repo_full_name} (action: {action})")
        
        # Only process opened and synchronize events
        if action not in ["opened", "synchronize"]:
            logger.info(f"Skipping PR event with action: {action}")
            # Return existing record if available
            existing = await self.db.get_pr_by_repo_and_number(repo_full_name, pr_number)
            if existing:
                return existing
            raise ValueError(f"Unexpected PR action: {action}")
        
        owner, repo = repo_full_name.split("/", 1)
        
        # Find linked issue
        issue_number = find_linked_issue(
            pr_body=pr_body,
            pr_labels=[label.get("name", "") for label in pr_data.get("labels", [])],
            branch_name=branch_name,
            commits=[]  # Could fetch commits if needed
        )
        
        issue_id = None
        checklist_items = []
        
        if issue_number:
            # Fetch issue record
            issue_record = await self.db.get_issue_by_repo_and_number(repo_full_name, issue_number)
            if issue_record:
                issue_id = issue_record.id
                # Convert checklist from dict to ChecklistItem objects
                from src.app.schemas.issue import ChecklistItem
                checklist_items = [
                    ChecklistItem(**item) if isinstance(item, dict) else item
                    for item in issue_record.checklist
                ]
        
        # Fetch PR diff and files
        try:
            pr_diff = await self.github.get_pr_diff(owner, repo, pr_number, installation_id)
            pr_files = await self.github.get_pr_files(owner, repo, pr_number, installation_id)
        except Exception as e:
            logger.error(f"Failed to fetch PR diff/files: {e}")
            pr_diff = ""
            pr_files = []
        
        # Generate test manifest
        test_manifest = self.generate_test_manifest(
            pr_number=pr_number,
            head_sha=head_sha,
            diff_text=pr_diff,
            files=pr_files,
            checklist=checklist_items
        )
        
        # Save or update PR record
        existing_pr = await self.db.get_pr_by_repo_and_number(repo_full_name, pr_number)
        
        if existing_pr:
            existing_pr.head_sha = head_sha
            existing_pr.issue_id = issue_id
            existing_pr.test_manifest = test_manifest.dict() if test_manifest else None
            existing_pr.validation_status = "pending"
            pr_record = await self.db.save_pr(existing_pr)
        else:
            pr_record = PRRecord(
                repo=repo_full_name,
                pr_number=pr_number,
                issue_id=issue_id,
                head_sha=head_sha,
                test_manifest=test_manifest.dict() if test_manifest else None,
                validation_status="pending"
            )
            pr_record = await self.db.save_pr(pr_record)
        
        # TODO: Trigger CI workflow if needed
        # This could be done via workflow_dispatch or by posting a comment
        # that triggers a GitHub Action
        
        return pr_record
    
    def generate_test_manifest(
        self,
        pr_number: int,
        head_sha: str,
        diff_text: str,
        files: List[Dict],
        checklist: List
    ) -> TestManifest:
        """
        Generate test manifest from PR diff and checklist.
        
        Args:
            pr_number: PR number
            head_sha: HEAD SHA of PR
            diff_text: Unified diff text
            files: List of changed files
            checklist: List of ChecklistItem objects
        
        Returns:
            TestManifest object
        """
        test_entries = []
        test_id_counter = 1
        
        # Extract changed symbols from diff
        changed_symbols = extract_changed_symbols(diff_text)
        file_types = get_changed_file_types(files)
        
        # Create mapping of files to symbols
        symbols_by_file = {}
        for symbol in changed_symbols:
            if symbol.file_path not in symbols_by_file:
                symbols_by_file[symbol.file_path] = []
            symbols_by_file[symbol.file_path].append(symbol)
        
        # Generate test entries for changed files
        for file_info in files:
            filename = file_info.get("filename", "")
            file_type = file_types.get(filename, "unknown")
            
            # Only generate tests for Python files for now
            if not filename.endswith(".py"):
                continue
            
            # Get symbols for this file
            symbols = symbols_by_file.get(filename, [])
            
            # Generate test for each function/class
            for symbol in symbols:
                if symbol.type == "function":
                    test_name = f"test_{symbol.name}_autoqa"
                    module_name = filename.replace("/", ".").replace(".py", "")
                    
                    # Map to checklist items if keywords match
                    checklist_ids = self._map_to_checklist(symbol.name, checklist)
                    
                    test_entry = TestManifestEntry(
                        test_id=f"T{test_id_counter}",
                        name=test_name,
                        framework="pytest",
                        target=filename,
                        checklist=checklist_ids
                    )
                    test_entries.append(test_entry)
                    test_id_counter += 1
        
        # If no tests generated from symbols, create generic tests based on checklist
        if not test_entries and checklist:
            for i, item in enumerate(checklist):
                if "test" in item.description.lower():
                    test_entry = TestManifestEntry(
                        test_id=f"T{test_id_counter}",
                        name=f"test_checklist_item_{item.id.lower()}_autoqa",
                        framework="pytest",
                        target=files[0].get("filename", "unknown") if files else "unknown",
                        checklist=[item.id]
                    )
                    test_entries.append(test_entry)
                    test_id_counter += 1
        
        return TestManifest(
            pr_number=pr_number,
            head_sha=head_sha,
            tests=test_entries
        )
    
    def _map_to_checklist(self, symbol_name: str, checklist: List) -> List[str]:
        """
        Map a symbol name to checklist items based on keyword matching.
        
        Args:
            symbol_name: Name of the symbol (function/class)
            checklist: List of ChecklistItem objects
        
        Returns:
            List of checklist item IDs
        """
        checklist_ids = []
        symbol_lower = symbol_name.lower()
        
        for item in checklist:
            item_lower = item.description.lower()
            
            # Extract keywords from symbol name
            symbol_words = set(symbol_lower.split("_"))
            
            # Extract keywords from checklist description
            item_words = set()
            for word in item.description.lower().split():
                # Remove common words
                if word not in ["the", "a", "an", "for", "and", "or", "but", "to", "of", "in", "on", "at"]:
                    item_words.add(word.strip(".,!?;:"))
            
            # Check for keyword overlap
            if symbol_words & item_words:
                checklist_ids.append(item.id)
        
        return checklist_ids

