#!/usr/bin/env python3
"""Generate sample webhook payloads for testing."""
import json
import sys
from typing import Dict

def generate_issue_opened_payload() -> Dict:
    """Generate sample issue opened webhook payload."""
    return {
        "action": "opened",
        "issue": {
            "number": 123,
            "title": "Add email validation",
            "body": """## Description
Add email validation to the signup form.

## Acceptance Criteria
- Must validate email format
- Must check for duplicate emails
- Should show clear error messages
- Must add unit tests
""",
            "state": "open",
            "labels": []
        },
        "repository": {
            "full_name": "owner/repo",
            "name": "repo",
            "owner": {
                "login": "owner"
            }
        },
        "installation": {
            "id": 12345
        }
    }


def generate_pr_opened_payload() -> Dict:
    """Generate sample PR opened webhook payload."""
    return {
        "action": "opened",
        "pull_request": {
            "number": 456,
            "title": "Add email validation",
            "body": "Fixes #123",
            "head": {
                "sha": "abc123def456",
                "ref": "feature/email-validation"
            },
            "base": {
                "ref": "main"
            },
            "labels": []
        },
        "repository": {
            "full_name": "owner/repo",
            "name": "repo",
            "owner": {
                "login": "owner"
            }
        },
        "installation": {
            "id": 12345
        }
    }


def generate_workflow_run_completed_payload() -> Dict:
    """Generate sample workflow run completed webhook payload."""
    return {
        "action": "completed",
        "workflow_run": {
            "id": 789,
            "head_sha": "abc123def456",
            "status": "completed",
            "conclusion": "success"
        },
        "repository": {
            "full_name": "owner/repo",
            "name": "repo",
            "owner": {
                "login": "owner"
            }
        },
        "installation": {
            "id": 12345
        }
    }


def main():
    """Generate sample webhook payload."""
    if len(sys.argv) < 2:
        print("Usage: python generate_sample_webhook.py <event_type>")
        print("Event types: issues, pull_request, workflow_run")
        sys.exit(1)
    
    event_type = sys.argv[1].lower()
    
    if event_type == "issues":
        payload = generate_issue_opened_payload()
        event_name = "issues"
    elif event_type == "pull_request" or event_type == "pr":
        payload = generate_pr_opened_payload()
        event_name = "pull_request"
    elif event_type == "workflow_run" or event_type == "workflow":
        payload = generate_workflow_run_completed_payload()
        event_name = "workflow_run"
    else:
        print(f"Unknown event type: {event_type}")
        sys.exit(1)
    
    # Print payload as JSON
    print(json.dumps(payload, indent=2))
    
    # Print instructions
    print("\n# To send this webhook:", file=sys.stderr)
    print(f"# curl -X POST http://localhost:8000/webhooks/github \\", file=sys.stderr)
    print(f"#   -H 'Content-Type: application/json' \\", file=sys.stderr)
    print(f"#   -H 'X-GitHub-Event: {event_name}' \\", file=sys.stderr)
    print(f"#   -H 'X-Hub-Signature-256: sha256=<calculated>' \\", file=sys.stderr)
    print(f"#   -d @- <<< '{json.dumps(payload)}'", file=sys.stderr)


if __name__ == "__main__":
    main()

