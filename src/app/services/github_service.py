"""GitHub API service wrapper."""
import httpx
import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from src.app.config import settings
from src.app.utils.security import generate_jwt_for_app
from src.app.exceptions import GitHubAPIError

logger = logging.getLogger(__name__)


class GitHubService:
    """Async wrapper around GitHub REST API."""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self):
        self._token_cache: Dict[int, tuple] = {}  # {installation_id: (token, expires_at)}
    
    async def get_installation_token(self, installation_id: int) -> str:
        """
        Get installation access token for a GitHub App installation.
        
        Args:
            installation_id: GitHub App installation ID
        
        Returns:
            Installation access token
        """
        # Check cache
        if installation_id in self._token_cache:
            token, expires_at = self._token_cache[installation_id]
            if expires_at > datetime.utcnow() + timedelta(minutes=5):  # Refresh 5 min early
                return token
        
        # Generate JWT for app
        jwt_token = generate_jwt_for_app()
        
        # Exchange JWT for installation token
        url = f"{self.BASE_URL}/app/installations/{installation_id}/access_tokens"
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                token = data["token"]
                expires_at_str = data.get("expires_at")
                
                # Parse expiration time
                expires_at = datetime.fromisoformat(expires_at_str.replace('Z', '+00:00'))
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=None)
                
                # Cache token
                self._token_cache[installation_id] = (token, expires_at)
                
                return token
            except httpx.HTTPError as e:
                logger.error(f"Error getting installation token: {e}")
                raise GitHubAPIError(f"Failed to get installation token: {e}")
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        installation_id: int,
        **kwargs
    ) -> httpx.Response:
        """Make authenticated request to GitHub API."""
        token = await self.get_installation_token(installation_id)
        url = f"{self.BASE_URL}{endpoint}" if not endpoint.startswith("http") else endpoint
        
        headers = kwargs.pop("headers", {})
        headers.update({
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json"
        })
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.request(method, url, headers=headers, **kwargs)
                
                # Handle rate limiting
                if response.status_code == 403 and "rate limit" in response.text.lower():
                    logger.warning("GitHub API rate limit exceeded")
                    raise GitHubAPIError("GitHub API rate limit exceeded")
                
                response.raise_for_status()
                return response
            except httpx.HTTPError as e:
                logger.error(f"GitHub API error: {e}")
                raise GitHubAPIError(f"GitHub API request failed: {e}")
    
    async def get_pr_diff(self, owner: str, repo: str, pr_number: int, installation_id: int) -> str:
        """Get unified diff for a pull request."""
        endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}"
        response = await self._make_request("GET", endpoint, installation_id)
        data = response.json()
        
        # Get the diff URL
        diff_url = data.get("diff_url")
        if diff_url:
            # Fetch the diff directly
            async with httpx.AsyncClient() as client:
                diff_response = await client.get(diff_url, headers={"Accept": "application/vnd.github.v3.diff"})
                return diff_response.text
        
        return ""
    
    async def get_pr_files(self, owner: str, repo: str, pr_number: int, installation_id: int) -> List[Dict]:
        """Get list of files changed in a PR."""
        endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}/files"
        response = await self._make_request("GET", endpoint, installation_id)
        return response.json()
    
    async def post_issue_comment(self, owner: str, repo: str, issue_number: int, body: str, installation_id: int) -> Dict:
        """Post a comment on an issue."""
        endpoint = f"/repos/{owner}/{repo}/issues/{issue_number}/comments"
        response = await self._make_request("POST", endpoint, installation_id, json={"body": body})
        return response.json()
    
    async def post_pr_comment(self, owner: str, repo: str, pr_number: int, body: str, installation_id: int) -> Dict:
        """Post a comment on a PR."""
        return await self.post_issue_comment(owner, repo, pr_number, body, installation_id)
    
    async def create_check_run(
        self,
        owner: str,
        repo: str,
        name: str,
        head_sha: str,
        status: str,
        conclusion: Optional[str] = None,
        installation_id: int = None
    ) -> Dict:
        """Create a check run."""
        if not installation_id:
            raise ValueError("installation_id is required")
        
        endpoint = f"/repos/{owner}/{repo}/check-runs"
        payload = {
            "name": name,
            "head_sha": head_sha,
            "status": status,
        }
        if conclusion:
            payload["conclusion"] = conclusion
        
        response = await self._make_request("POST", endpoint, installation_id, json=payload)
        return response.json()
    
    async def merge_pr(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        merge_method: str = "squash",
        commit_title: Optional[str] = None,
        installation_id: int = None
    ) -> Dict:
        """Merge a pull request."""
        if not installation_id:
            raise ValueError("installation_id is required")
        
        endpoint = f"/repos/{owner}/{repo}/pulls/{pr_number}/merge"
        payload = {"merge_method": merge_method}
        if commit_title:
            payload["commit_title"] = commit_title
        
        response = await self._make_request("PUT", endpoint, installation_id, json=payload)
        return response.json()
    
    async def get_branch_protection(self, owner: str, repo: str, branch: str, installation_id: int) -> Optional[Dict]:
        """Get branch protection rules."""
        endpoint = f"/repos/{owner}/{repo}/branches/{branch}/protection"
        try:
            response = await self._make_request("GET", endpoint, installation_id)
            return response.json()
        except GitHubAPIError:
            # Branch may not have protection
            return None
    
    async def trigger_workflow_dispatch(
        self,
        owner: str,
        repo: str,
        workflow_id: str,
        ref: str,
        inputs: Dict,
        installation_id: int
    ) -> bool:
        """Trigger a workflow dispatch event."""
        endpoint = f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches"
        payload = {
            "ref": ref,
            "inputs": inputs
        }
        try:
            await self._make_request("POST", endpoint, installation_id, json=payload)
            return True
        except GitHubAPIError as e:
            logger.error(f"Failed to trigger workflow: {e}")
            return False
    
    async def download_artifact(
        self,
        owner: str,
        repo: str,
        artifact_id: int,
        installation_id: int
    ) -> bytes:
        """Download a workflow artifact."""
        endpoint = f"/repos/{owner}/{repo}/actions/artifacts/{artifact_id}/zip"
        response = await self._make_request("GET", endpoint, installation_id)
        return response.content
    
    async def list_workflow_run_artifacts(
        self,
        owner: str,
        repo: str,
        run_id: int,
        installation_id: int
    ) -> List[Dict]:
        """List artifacts for a workflow run."""
        endpoint = f"/repos/{owner}/{repo}/actions/runs/{run_id}/artifacts"
        response = await self._make_request("GET", endpoint, installation_id)
        data = response.json()
        return data.get("artifacts", [])

