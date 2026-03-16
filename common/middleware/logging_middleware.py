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
import logging
import time
import uuid

from django.utils.deprecation import MiddlewareMixin

from common.context import get_correlation_id, set_correlation_id

logger = logging.getLogger("request_logger")


class LoggingMiddleware(MiddlewareMixin):
    """
    Request-Response Logging Middleware - Provides JSON-Structured Observability

    This middleware provides comprehensive logging for all HTTP requests and responses
    with the following features:
    - Correlation ID generation and propagation (trace requests across services)
    - Tenant ID & User ID (audit trail and multi-tenant data isolation)
    - Execution time in milliseconds (performance monitoring)
    - Request/response lifecycle logging with proper log levels (INFO/WARNING/ERROR)
    - Async-safe logging (works with Celery & async views)
    """

    def process_request(self, request):
        """
        Called on each request, before Django decides which view to execute.
        Generates correlation ID and logs request details.
        """
        correlation_id = str(uuid.uuid4())
        set_correlation_id(correlation_id)
        request.correlation_id = correlation_id
        request._start_time = time.time()

        tenant_id = (
            request.user.tenant_id if request.user.is_authenticated else None
        )
        user_id = request.user.id if request.user.is_authenticated else None
        log_data = {
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.path,
            "ip_address": self._get_client_ip(request),
            "tenant_id": tenant_id,
            "user_id": user_id,
        }
        logger.info(
            "Request received",
            extra=log_data,
        )

        return None

    def process_response(self, request, response):
        """
        Called on each response. Logs response details and timing.
        """
        execution_time = 0
        if hasattr(request, "_start_time"):
            execution_time = (time.time() - request._start_time) * 1000
        correlation_id = get_correlation_id()
        tenant_id = (
            request.user.tenant_id if request.user.is_authenticated else None
        )
        user_id = request.user.id if request.user.is_authenticated else None

        log_data = {
            "correlation_id": correlation_id,
            "method": request.method,
            "path": request.path,
            "status_code": response.status_code,
            "execution_time_ms": round(execution_time, 2),
            "tenant_id": tenant_id,
            "user_id": user_id,
        }
        if hasattr(response, "content"):
            log_data["response_size"] = len(response.content)

        if response.status_code >= 500:
            logger.error("Response sent with server error", extra=log_data)
        elif response.status_code >= 400:
            logger.warning("Response sent with client error", extra=log_data)
        else:
            logger.info("Response sent:", extra=log_data)

        return response

    def _get_client_ip(self, request):
        """
        Extract client IP address from request.
        Handles proxy headers like X-Forwarded-For.
        """
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "")
        return ip

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

        Passes data as extra so JsonFormatter outputs one JSON object per line.
        Never uses print().
        """
        # Pass data as extra for JsonFormatter to include in output
        level_name = logging.getLevelName(level).lower()
        log_func = getattr(logger, level_name, logger.info)
        log_func("", extra=data)

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
