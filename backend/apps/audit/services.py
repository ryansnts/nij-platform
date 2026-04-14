from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.http import HttpRequest
    from apps.authentication.models import User


def log_action(user: "User", action: str, details: str = "", request: "HttpRequest | None" = None):
    """Create an audit log entry. Safe to call from anywhere."""
    from .models import AuditLog

    ip = None
    ua = ""
    if request:
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        ip = x_forwarded.split(",")[0].strip() if x_forwarded else request.META.get("REMOTE_ADDR")
        ua = request.META.get("HTTP_USER_AGENT", "")[:500]

    AuditLog.objects.create(
        user=user,
        username=user.username if user else "system",
        action=action,
        details=details,
        ip_address=ip,
        user_agent=ua,
    )
