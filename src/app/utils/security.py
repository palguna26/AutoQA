"""Security utilities for GitHub webhook verification and JWT generation."""
import hmac
import hashlib
import time
import jwt
from typing import Optional
from datetime import datetime, timedelta

from src.app.config import settings
from src.app.exceptions import WebhookVerificationError


def verify_github_signature(secret: str, signature_header: str, body: bytes) -> bool:
    """
    Verify GitHub webhook HMAC signature.
    
    Args:
        secret: Webhook secret
        signature_header: Value from X-Hub-Signature-256 header (format: sha256=...)
        body: Raw request body bytes
    
    Returns:
        True if signature is valid, False otherwise
    """
    if not signature_header.startswith("sha256="):
        return False
    
    expected_signature = signature_header[7:]  # Remove "sha256=" prefix
    
    # Compute HMAC-SHA256
    mac = hmac.new(
        secret.encode('utf-8'),
        msg=body,
        digestmod=hashlib.sha256
    )
    computed_signature = mac.hexdigest()
    
    # Constant-time comparison to prevent timing attacks
    return hmac.compare_digest(computed_signature, expected_signature)


def generate_jwt_for_app() -> str:
    """
    Generate JWT token for GitHub App authentication.
    
    Returns:
        JWT token string
    """
    now = datetime.utcnow()
    
    # JWT payload for GitHub App
    payload = {
        "iat": int(now.timestamp()) - 60,  # Issued at (1 minute ago for clock skew)
        "exp": int((now + timedelta(minutes=10)).timestamp()),  # Expires in 10 minutes
        "iss": settings.github_app_id  # GitHub App ID
    }
    
    # Encode JWT with RS256 algorithm
    token = jwt.encode(
        payload,
        settings.github_private_key.encode('utf-8') if isinstance(settings.github_private_key, str) else settings.github_private_key,
        algorithm="RS256"
    )
    
    return token

