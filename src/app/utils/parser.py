"""Parser utilities for extracting information from issue bodies and PRs."""
import re
from typing import List, Optional


def extract_acceptance_criteria(issue_body: str) -> List[str]:
    """
    Extract acceptance criteria from issue body.
    
    Looks for sections like:
    - "Acceptance Criteria:"
    - "Acceptance Criteria"
    - Bullet points with - or *
    
    Args:
        issue_body: Raw issue body text
    
    Returns:
        List of acceptance criteria strings
    """
    if not issue_body:
        return []
    
    criteria = []
    
    # Pattern 1: Look for "Acceptance Criteria:" or "Acceptance Criteria" section
    patterns = [
        r'(?:##?\s*)?Acceptance\s+Criteria:?\s*\n([\s\S]*?)(?=\n##|\Z)',
        r'(?:##?\s*)?AC:?\s*\n([\s\S]*?)(?=\n##|\Z)',
        r'(?:##?\s*)?Requirements:?\s*\n([\s\S]*?)(?=\n##|\Z)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, issue_body, re.IGNORECASE | re.MULTILINE)
        if match:
            content = match.group(1).strip()
            # Extract bullet points
            bullets = re.findall(r'^[\s]*[-*•]\s+(.+)$', content, re.MULTILINE)
            if bullets:
                criteria.extend([b.strip() for b in bullets if b.strip()])
                break
    
    # Pattern 2: If no structured section found, look for any bullet points mentioning "must", "should", "need"
    if not criteria:
        # Look for bullet points with requirement keywords
        requirement_pattern = r'^[\s]*[-*•]\s+(.+?(?:must|should|need|require|ensure|verify).+)$'
        matches = re.findall(requirement_pattern, issue_body, re.IGNORECASE | re.MULTILINE)
        criteria.extend([m.strip() for m in matches if m.strip()])
    
    # Clean up and deduplicate
    criteria = [c for c in criteria if len(c) > 10]  # Filter out too short items
    seen = set()
    unique_criteria = []
    for item in criteria:
        if item.lower() not in seen:
            seen.add(item.lower())
            unique_criteria.append(item)
    
    return unique_criteria


def find_linked_issue(pr_body: str, pr_labels: List[str], branch_name: str, commits: List[str] = None) -> Optional[int]:
    """
    Find linked issue number from PR body, labels, branch name, or commits.
    
    Args:
        pr_body: PR description/body
        pr_labels: List of PR labels
        branch_name: Branch name (e.g., "feature/issue-123" or "fix-123")
        commits: List of commit messages
    
    Returns:
        Issue number if found, None otherwise
    """
    # Pattern 1: Look for #123 in PR body
    if pr_body:
        matches = re.findall(r'#(\d+)', pr_body)
        if matches:
            # Return the first issue number found
            return int(matches[0])
        
        # Look for "Fixes #123", "Closes #123", etc.
        close_patterns = [
            r'(?:fixes?|closes?|resolves?)\s+#(\d+)',
            r'(?:fixes?|closes?|resolves?):\s*#(\d+)',
        ]
        for pattern in close_patterns:
            match = re.search(pattern, pr_body, re.IGNORECASE)
            if match:
                return int(match.group(1))
    
    # Pattern 2: Extract from branch name (e.g., "feature/issue-123", "fix-123", "123-feature")
    if branch_name:
        # Try patterns like "issue-123", "fix-123", "123-"
        branch_matches = re.findall(r'(?:issue[-_]?|fix[-_]?)?(\d+)', branch_name, re.IGNORECASE)
        if branch_matches:
            return int(branch_matches[0])
    
    # Pattern 3: Extract from commit messages
    if commits:
        for commit_msg in commits:
            matches = re.findall(r'#(\d+)', commit_msg)
            if matches:
                return int(matches[0])
    
    # Pattern 4: Look for issue label (e.g., "issue-123")
    if pr_labels:
        for label in pr_labels:
            match = re.search(r'issue[-_]?(\d+)', label, re.IGNORECASE)
            if match:
                return int(match.group(1))
    
    return None

