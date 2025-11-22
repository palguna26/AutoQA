"""Custom exceptions for AutoQA."""


class AutoQAException(Exception):
    """Base exception for AutoQA."""
    pass


class GitHubAPIError(AutoQAException):
    """Error interacting with GitHub API."""
    pass


class DatabaseError(AutoQAException):
    """Database operation error."""
    pass


class ValidationError(AutoQAException):
    """Data validation error."""
    pass


class LLMError(AutoQAException):
    """LLM API error."""
    pass


class WebhookVerificationError(AutoQAException):
    """Webhook signature verification failed."""
    pass

