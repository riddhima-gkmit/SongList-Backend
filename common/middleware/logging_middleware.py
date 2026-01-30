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

