"""GitHub webhook endpoint."""
import logging
from fastapi import APIRouter, Request, Response, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
import json

from src.app.config import settings
from src.app.utils.security import verify_github_signature
from src.app.exceptions import WebhookVerificationError
from src.app.logging_config import get_logger
from src.app.deps import get_db_session
from src.app.adapters.db_adapter import DBAdapter
from src.app.adapters.llm_adapter import LLMAdapter
from src.app.services.github_service import GitHubService
from src.app.services.checklist_service import ChecklistService
from src.app.services.testgen_service import TestGenService
from src.app.services.ci_mapper import CIMapper
from src.app.services.merge_service import MergeService

logger = get_logger(__name__)
router = APIRouter()

# In-memory cache for event deduplication (use Redis in production)
processed_events = set()
MAX_CACHE_SIZE = 10000


@router.post("/webhooks/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = None,
    x_hub_signature_256: str = None,
    x_github_delivery: str = None
):
    """
    GitHub webhook endpoint.
    
    Handles:
    - issues.opened: Generate checklist
    - pull_request.opened, pull_request.synchronize: Generate test manifest
    - workflow_run.completed: Map CI results to checklist
    """
    # Get headers
    if not x_github_event:
        x_github_event = request.headers.get("X-GitHub-Event")
    if not x_hub_signature_256:
        x_hub_signature_256 = request.headers.get("X-Hub-Signature-256")
    if not x_github_delivery:
        x_github_delivery = request.headers.get("X-GitHub-Delivery")
    
    # Get raw body for signature verification
    body_bytes = await request.body()
    
    # Verify webhook signature
    if not x_hub_signature_256:
        logger.error("Missing X-Hub-Signature-256 header")
        raise HTTPException(status_code=401, detail="Missing signature header")
    
    if not verify_github_signature(settings.github_webhook_secret, x_hub_signature_256, body_bytes):
        logger.error("Webhook signature verification failed")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse JSON payload
    try:
        payload = json.loads(body_bytes.decode('utf-8'))
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Event deduplication
    if x_github_delivery:
        if x_github_delivery in processed_events:
            logger.info(f"Event {x_github_delivery} already processed, skipping")
            return JSONResponse(content={"status": "already_processed"})
        
        # Add to cache
        processed_events.add(x_github_delivery)
        if len(processed_events) > MAX_CACHE_SIZE:
            # Remove oldest (simple FIFO, use LRU in production)
            processed_events.pop()
    
    # Route events to appropriate handlers
    event_type = x_github_event
    action = payload.get("action")
    
    logger.info(f"Processing event: {event_type}.{action} (delivery: {x_github_delivery})")
    
    # Handle events asynchronously
    if event_type == "issues" and action == "opened":
        background_tasks.add_task(handle_issue_event, payload)
        return JSONResponse(content={"status": "accepted"})
    
    elif event_type == "pull_request" and action in ["opened", "synchronize"]:
        background_tasks.add_task(handle_pr_event, payload)
        return JSONResponse(content={"status": "accepted"})
    
    elif event_type == "workflow_run" and action == "completed":
        background_tasks.add_task(handle_workflow_run_event, payload)
        return JSONResponse(content={"status": "accepted"})
    
    else:
        logger.info(f"Event {event_type}.{action} not handled, ignoring")
        return JSONResponse(content={"status": "ignored"})


async def handle_issue_event(payload: dict):
    """Handle issue opened event."""
    try:
        from src.app.models.base import get_db
        async for session in get_db():
            db = DBAdapter(session)
            github = GitHubService()
            llm = LLMAdapter()
            service = ChecklistService(db, github, llm)
            
            await service.handle_issue_event(payload)
            break
    except Exception as e:
        logger.error(f"Error handling issue event: {e}", exc_info=True)


async def handle_pr_event(payload: dict):
    """Handle PR opened/synchronize event."""
    try:
        from src.app.models.base import get_db
        async for session in get_db():
            db = DBAdapter(session)
            github = GitHubService()
            service = TestGenService(db, github)
            
            await service.handle_pr_event(payload)
            break
    except Exception as e:
        logger.error(f"Error handling PR event: {e}", exc_info=True)


async def handle_workflow_run_event(payload: dict):
    """Handle workflow_run completed event."""
    try:
        from src.app.models.base import get_db
        async for session in get_db():
            db = DBAdapter(session)
            github = GitHubService()
            merge_service = MergeService(github)
            service = CIMapper(db, github, merge_service)
            
            await service.handle_workflow_run(payload)
            break
    except Exception as e:
        logger.error(f"Error handling workflow_run event: {e}", exc_info=True)


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(content={"status": "healthy", "service": "autoqa"})

