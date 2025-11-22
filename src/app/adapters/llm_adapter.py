"""LLM adapter for different providers (Groq, OpenAI, etc.)."""
from typing import List, Optional
import json
import logging

from src.app.config import settings
from src.app.schemas.issue import ChecklistItem
from src.app.schemas.pr import TestManifest, TestManifestEntry

logger = logging.getLogger(__name__)


class LLMAdapter:
    """Adapter for LLM providers."""
    
    def __init__(self):
        self.provider = settings.llm_provider.lower()
        self.api_key = settings.llm_api_key
        self._client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the LLM client based on provider."""
        if self.provider == "none":
            logger.info("LLM provider set to 'none', using heuristic methods only")
            return
        
        if not self.api_key:
            logger.warning(f"LLM provider '{self.provider}' configured but no API key provided")
            return
        
        if self.provider == "groq":
            try:
                from groq import Groq
                self._client = Groq(api_key=self.api_key)
                logger.info("Groq client initialized")
            except ImportError:
                logger.error("groq package not installed. Install with: pip install groq")
        
        elif self.provider == "openai":
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=self.api_key)
                logger.info("OpenAI client initialized")
            except ImportError:
                logger.error("openai package not installed. Install with: pip install openai")
        
        else:
            logger.warning(f"Unknown LLM provider: {self.provider}")
    
    async def parse_issue_to_checklist(self, issue_text: str) -> List[ChecklistItem]:
        """
        Parse issue text to generate checklist items.
        
        Args:
            issue_text: Issue description/body
        
        Returns:
            List of ChecklistItem objects
        """
        if self.provider == "none" or not self._client:
            # Return empty list - will be handled by heuristic parser
            return []
        
        try:
            if self.provider == "groq":
                return await self._parse_with_groq(issue_text)
            elif self.provider == "openai":
                return await self._parse_with_openai(issue_text)
        except Exception as e:
            logger.error(f"Error parsing issue with LLM: {e}")
            return []
        
        return []
    
    async def _parse_with_groq(self, issue_text: str) -> List[ChecklistItem]:
        """Parse issue using Groq."""
        if not self._client:
            return []
        
        prompt = f"""Parse the following GitHub issue description and extract acceptance criteria as a checklist.
Return a JSON array of checklist items. Each item should have:
- id: unique identifier (C1, C2, etc.)
- description: clear description of the requirement
- required: boolean indicating if this is a required item
- tags: array of relevant tags

Issue description:
{issue_text}

Return only valid JSON array, no markdown formatting.
"""
        
        try:
            response = self._client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts acceptance criteria from GitHub issues and formats them as structured checklists."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            # Handle different response formats
            items = data.get("items", data.get("checklist", []))
            
            return [
                ChecklistItem(
                    id=item.get("id", f"C{i+1}"),
                    description=item.get("description", ""),
                    required=item.get("required", True),
                    tags=item.get("tags", [])
                )
                for i, item in enumerate(items)
            ]
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return []
    
    async def _parse_with_openai(self, issue_text: str) -> List[ChecklistItem]:
        """Parse issue using OpenAI."""
        if not self._client:
            return []
        
        prompt = f"""Parse the following GitHub issue description and extract acceptance criteria as a checklist.
Return a JSON object with an "items" array. Each item should have:
- id: unique identifier (C1, C2, etc.)
- description: clear description of the requirement
- required: boolean indicating if this is a required item
- tags: array of relevant tags

Issue description:
{issue_text}

Return only valid JSON, no markdown formatting.
"""
        
        try:
            response = await self._client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that extracts acceptance criteria from GitHub issues and formats them as structured checklists."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            
            items = data.get("items", data.get("checklist", []))
            
            return [
                ChecklistItem(
                    id=item.get("id", f"C{i+1}"),
                    description=item.get("description", ""),
                    required=item.get("required", True),
                    tags=item.get("tags", [])
                )
                for i, item in enumerate(items)
            ]
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            return []
    
    async def generate_tests_from_diff(self, diff_text: str, checklist: List[ChecklistItem]) -> Optional[TestManifest]:
        """
        Generate test manifest from diff and checklist.
        
        Currently returns None - test generation uses heuristics.
        LLM-based test generation can be added here in the future.
        """
        # TODO: Implement LLM-based test generation
        return None
    
    async def generate_report_summary(self, checklist: List[ChecklistItem], test_results: List) -> str:
        """
        Generate a summary report from checklist and test results.
        
        Currently returns a simple formatted string.
        LLM-based summary generation can be added here in the future.
        """
        # Simple heuristic-based summary for now
        required_count = sum(1 for item in checklist if item.required)
        passed_count = sum(1 for result in test_results if result.status == "passed")
        
        return f"Required items passed: {passed_count}/{required_count}"

