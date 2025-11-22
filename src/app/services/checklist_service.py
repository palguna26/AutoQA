"""Service for generating and managing issue checklists."""
import logging
import yaml
from typing import Dict, List

from src.app.models import IssueRecord
from src.app.schemas.issue import ChecklistItem
from src.app.adapters.db_adapter import DBAdapter
from src.app.adapters.llm_adapter import LLMAdapter
from src.app.services.github_service import GitHubService
from src.app.utils.parser import extract_acceptance_criteria

logger = logging.getLogger(__name__)


class ChecklistService:
    """Service for handling issue checklist generation."""
    
    def __init__(self, db_adapter: DBAdapter, github_service: GitHubService, llm_adapter: LLMAdapter):
        self.db = db_adapter
        self.github = github_service
        self.llm = llm_adapter
    
    async def handle_issue_event(self, event: Dict) -> IssueRecord:
        """
        Handle GitHub issue opened event.
        
        Args:
            event: GitHub webhook event payload
        
        Returns:
            IssueRecord object
        """
        issue_data = event.get("issue", {})
        repo_data = event.get("repository", {})
        
        issue_number = issue_data.get("number")
        issue_body = issue_data.get("body", "")
        repo_full_name = repo_data.get("full_name")
        installation_id = event.get("installation", {}).get("id")
        
        if not all([issue_number, repo_full_name, installation_id]):
            raise ValueError("Missing required fields in issue event")
        
        logger.info(f"Processing issue #{issue_number} in {repo_full_name}")
        
        # Extract acceptance criteria using heuristics
        criteria_texts = extract_acceptance_criteria(issue_body)
        
        # Try to generate checklist using LLM if enabled
        llm_checklist = []
        if self.llm.provider != "none":
            try:
                llm_checklist = await self.llm.parse_issue_to_checklist(issue_body)
            except Exception as e:
                logger.warning(f"LLM checklist generation failed: {e}")
        
        # Merge heuristic and LLM results
        checklist_items = self._normalize_checklist(criteria_texts, llm_checklist)
        
        # Check if issue already exists
        existing_issue = await self.db.get_issue_by_repo_and_number(repo_full_name, issue_number)
        
        if existing_issue:
            # Update existing issue
            existing_issue.checklist = [item.dict() for item in checklist_items]
            existing_issue.status = issue_data.get("state", "open")
            issue_record = await self.db.save_issue(existing_issue)
        else:
            # Create new issue record
            issue_record = IssueRecord(
                repo=repo_full_name,
                issue_number=issue_number,
                checklist=[item.dict() for item in checklist_items],
                status=issue_data.get("state", "open")
            )
            issue_record = await self.db.save_issue(issue_record)
        
        # Post checklist as comment on issue
        owner, repo = repo_full_name.split("/", 1)
        comment_body = self._format_checklist_comment(checklist_items)
        
        try:
            await self.github.post_issue_comment(
                owner=owner,
                repo=repo,
                issue_number=issue_number,
                body=comment_body,
                installation_id=installation_id
            )
            
            # Add label if possible (requires additional API call)
            # This would require 'Issues: write' permission
            logger.info(f"Posted checklist comment on issue #{issue_number}")
        except Exception as e:
            logger.error(f"Failed to post checklist comment: {e}")
        
        return issue_record
    
    def _normalize_checklist(self, criteria_texts: List[str], llm_checklist: List[ChecklistItem]) -> List[ChecklistItem]:
        """
        Normalize and merge heuristic and LLM-generated checklists.
        
        Args:
            criteria_texts: List of criteria strings from heuristics
            llm_checklist: List of ChecklistItem from LLM
        
        Returns:
            List of normalized ChecklistItem objects
        """
        items = []
        
        # Start with LLM items if available
        if llm_checklist:
            items.extend(llm_checklist)
        
        # Add heuristic items that aren't already covered
        existing_descriptions = {item.description.lower() for item in items}
        
        for i, criteria_text in enumerate(criteria_texts):
            criteria_lower = criteria_text.lower()
            
            # Skip if already covered by LLM
            if any(criteria_lower in desc or desc in criteria_lower for desc in existing_descriptions):
                continue
            
            # Determine if required (heuristic: check for keywords)
            required = any(keyword in criteria_text.lower() for keyword in ["must", "required", "shall", "need"])
            
            # Extract tags from criteria text
            tags = []
            if "test" in criteria_text.lower():
                tags.append("testing")
            if "validation" in criteria_text.lower() or "validate" in criteria_text.lower():
                tags.append("validation")
            if "error" in criteria_text.lower() or "exception" in criteria_text.lower():
                tags.append("error-handling")
            
            items.append(ChecklistItem(
                id=f"C{len(items) + 1}",
                description=criteria_text,
                required=required,
                tags=tags
            ))
        
        return items
    
    def _format_checklist_comment(self, checklist_items: List[ChecklistItem]) -> str:
        """Format checklist as GitHub comment."""
        comment = "## ✅ AutoQA Checklist\n\n"
        comment += "This checklist was automatically generated from the issue description.\n\n"
        
        if not checklist_items:
            comment += "⚠️ No acceptance criteria found in the issue description.\n"
            comment += "Please add acceptance criteria using a section like:\n\n"
            comment += "```\n## Acceptance Criteria\n- Criterion 1\n- Criterion 2\n```\n"
            return comment
        
        # Format as checkbox list
        for item in checklist_items:
            checkbox = "- [ ]" if item.required else "- [ ] *(optional)*"
            required_badge = "**Required**" if item.required else "Optional"
            tags_str = " ".join([f"`{tag}`" for tag in item.tags]) if item.tags else ""
            
            comment += f"{checkbox} **{item.id}**: {item.description} {required_badge}\n"
            if tags_str:
                comment += f"  {tags_str}\n"
        
        # Add YAML format for reference
        comment += "\n---\n\n"
        comment += "<details>\n<summary>Checklist JSON</summary>\n\n"
        comment += "```yaml\n"
        checklist_dict = [item.dict() for item in checklist_items]
        comment += yaml.dump(checklist_dict, default_flow_style=False)
        comment += "```\n\n</details>\n"
        
        return comment

