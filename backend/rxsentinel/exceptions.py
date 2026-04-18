"""Shared exception types."""
from __future__ import annotations


class RxSentinelError(Exception):
    """Root for all RxSentinel-specific exceptions."""


class ToolError(RxSentinelError):
    """Raised when a tool fails after exhausting retries."""


class AgentError(RxSentinelError):
    """Raised when an agent fails to produce valid output."""


class ValidationFailed(RxSentinelError):
    """Raised when input validation rejects a request."""
