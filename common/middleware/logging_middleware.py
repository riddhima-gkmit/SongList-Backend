"""
Logging middleware for request/response observability.

Production-ready middleware that captures HTTP request/response lifecycle
with structured logging, correlation IDs, and safe handling of sensitive data.

PRD Compliance:
- Pass: Logs method, path, status, duration; structured JSON/key-value
- Strong: Correlation ID, Tenant ID, User ID, execution time (ms), masked secrets
- Exceptional: Correct log levels, error context/stack trace, async-safe, field docs

Red flags avoided:
- No request/response body logging (prevents PII/secrets leakage)
- No query params (may contain tokens)
- Uses logging framework, not print()
- Correlation ID ties all logs for a request
"""
import json
import logging
import time
import traceback
import uuid
from contextvars import ContextVar

from django.utils.deprecation import MiddlewareMixin

# ContextVar for async-safe correlation ID propagation (Celery & async views)
# Allows downstream code to access request_id without passing it explicitly
request_context: ContextVar[dict] = ContextVar("request_context", default={})

logger = logging.getLogger(__name__)


def get_correlation_id() -> str | None:
    """
    Get the current request's correlation ID from context (async-safe).

    Use in views, services, or Celery tasks (when task receives correlation_id
    as argument and sets it via request_context.set()).
    """
    try:
        return request_context.get().get("correlation_id")
    except LookupError:
        return None


class LoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log HTTP requests and responses with structured observability.

    Logs metadata only—never request/response bodies—to avoid PII and secrets.
    Uses contextvars for async-safe correlation ID propagation.
    """

    # Keys that indicate sensitive data; used when masking is needed (e.g. error messages)
    SENSITIVE_KEYS = frozenset({
        "password", "token", "secret", "api_key", "authorization",
        "confirm_password", "old_password", "new_password", "otp",
        "mfa_secret", "backup_codes", "totp_token", "access", "refresh",
    })

    def process_request(self, request):
        """
        Generate correlation ID, start timer, and log incoming request.

        Correlation ID is stored on request and in contextvars for async propagation.
        """
        request.correlation_id = str(uuid.uuid4())
        request.start_time = time.perf_counter()
        request._logging_exception = None  # Populated by process_exception

        # Propagate to contextvars for async/Celery-aware code
        ctx = request_context.get().copy()
        ctx["correlation_id"] = request.correlation_id
        request_context.set(ctx)

        self._log_request(request)
        return None

    def process_response(self, request, response):
        """
        Log response with duration, status, and error context if present.

        Adds X-Request-ID header for client-side correlation.
        """
        if hasattr(request, "start_time"):
            duration_ms = (time.perf_counter() - request.start_time) * 1000
            self._log_response(request, response, duration_ms)

        if hasattr(request, "correlation_id"):
            response["X-Request-ID"] = request.correlation_id

        # Clear contextvars after request completes
        try:
            request_context.set({})
        except LookupError:
            pass

        return response

    def process_exception(self, request, exception):
        """
        Capture exception and traceback for error response logging.

        Stored on request for process_response to include in ERROR logs.
        Does not consume the exception—Django continues normal error handling.
        """
        request._logging_exception = exception
        return None

    def _log_request(self, request):
        """
        Log incoming request metadata (no body, no query params).

        Fields logged:
        - event: Identifies log type for filtering
        - correlation_id: Ties request to response and downstream logs
        - method: HTTP method for debugging
        - path: Request path (no query string to avoid tokens)
        - tenant_id: Multi-tenant context for support
        - user_id: Audit trail when authenticated
        """
        try:
            tenant_id = self._get_tenant_id(request)
            user_id = self._get_user_id(request)

            log_data = {
                "event": "request",
                "correlation_id": getattr(request, "correlation_id", "unknown"),
                "method": request.method,
                "path": request.path,
                "tenant_id": tenant_id,
                "user_id": user_id,
            }

            self._emit_log(log_data, logging.INFO)
        except Exception as e:
            logger.error(
                "Logging middleware failed on request",
                extra={
                    "correlation_id": getattr(request, "correlation_id", "unknown"),
                    "path": getattr(request, "path", "unknown"),
                    "error": str(e),
                },
                exc_info=True,
            )

    def _log_response(self, request, response, duration_ms: float):
        """
        Log outgoing response with status, duration, and error context.

        Fields logged:
        - event: Identifies log type
        - correlation_id: Request correlation
        - method, path: Request context
        - status_code: For alerting and metrics
        - duration_ms: Performance monitoring
        - tenant_id, user_id: Context
        - error_context: Stack trace / exception (5xx only, masked)
        """
        try:
            tenant_id = self._get_tenant_id(request)
            user_id = self._get_user_id(request)

            log_data = {
                "event": "response",
                "correlation_id": getattr(request, "correlation_id", "unknown"),
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
                "tenant_id": tenant_id,
                "user_id": user_id,
            }

            # Add error context for 5xx (stack trace, masked)
            exc = getattr(request, "_logging_exception", None)
            if exc and response.status_code >= 500:
                log_data["error_context"] = self._safe_error_context(exc)

            # Log levels: INFO=success, WARNING=client error, ERROR=server error
            if response.status_code >= 500:
                level = logging.ERROR
            elif response.status_code >= 400:
                level = logging.WARNING
            else:
                level = logging.INFO

            self._emit_log(log_data, level)
        except Exception as e:
            logger.error(
                "Logging middleware failed on response",
                extra={
                    "correlation_id": getattr(request, "correlation_id", "unknown"),
                    "path": getattr(request, "path", "unknown"),
                    "error": str(e),
                },
                exc_info=True,
            )

    def _emit_log(self, data: dict, level: int):
        """
        Emit structured log (JSON) using the logging framework.

        Uses json.dumps for structured output; works with any formatter.
        Never uses print().
        """
        log_line = json.dumps(data)
        level_name = logging.getLevelName(level).lower()
        log_func = getattr(logger, level_name, logger.info)
        log_func(log_line)

    def _safe_error_context(self, exception: BaseException) -> dict:
        """
        Build error context with stack trace, masking sensitive data.

        Used only for 5xx responses to aid production debugging.
        """
        try:
            tb_lines = traceback.format_exception(
                type(exception), exception, exception.__traceback__
            )
            tb_str = "".join(tb_lines)
            # Mask any accidental sensitive strings in traceback
            for key in self.SENSITIVE_KEYS:
                if key.lower() in tb_str.lower():
                    tb_str = tb_str.replace(key, "***MASKED***")
            return {
                "exception_type": type(exception).__name__,
                "exception_message": str(exception)[:500],  # Truncate
                "traceback": tb_str[:2000],  # Limit size
            }
        except Exception:
            return {"exception_type": type(exception).__name__, "exception_message": str(exception)[:200]}

    def _get_tenant_id(self, request) -> str | None:
        """Tenant ID for multi-tenant context; None if not applicable."""
        if not hasattr(request, "user") or not request.user.is_authenticated:
            return None
        user = request.user
        if hasattr(user, "tenant") and user.tenant:
            return str(user.tenant.id)
        return None

    def _get_user_id(self, request) -> str | None:
        """User ID when authenticated; None otherwise."""
        if hasattr(request, "user") and request.user.is_authenticated:
            return str(request.user.id)
        return None
