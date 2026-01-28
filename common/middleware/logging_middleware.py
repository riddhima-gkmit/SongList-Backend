"""
Logging middleware for request/response observability.

Captures all HTTP requests and responses with structured JSON logging,
including correlation IDs, duration tracking, and sensitive data masking.
"""
import time
import uuid
import json
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class LoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all HTTP requests and responses with structured logging.
    
    Features:
    - Unique correlation ID per request
    - Request/response logging with duration
    - Tenant and user context
    - Sensitive data masking
    - Structured JSON format
    """
    
    SENSITIVE_KEYS = {
        'password', 'token', 'secret', 'api_key', 'authorization',
        'confirm_password', 'old_password', 'new_password', 'otp',
        'mfa_secret', 'backup_codes', 'totp_token'
    }
    
    def process_request(self, request):
        """Generate correlation ID and start timer."""
        request.correlation_id = str(uuid.uuid4())
        request.start_time = time.time()
        
        # Log incoming request
        self._log_request(request)
        
        return None
    
    def process_response(self, request, response):
        """Log response with duration."""
        if hasattr(request, 'start_time'):
            duration = (time.time() - request.start_time) * 1000  # ms
            self._log_response(request, response, duration)
        
        # Add correlation ID to response headers
        if hasattr(request, 'correlation_id'):
            response['X-Request-ID'] = request.correlation_id
        
        return response
    
    def _log_request(self, request):
        """Log incoming request with masked sensitive data."""
        try:
            # Get request body
            request_body = {}
            if request.method in ['POST', 'PUT', 'PATCH']:
                try:
                    if request.content_type == 'application/json':
                        request_body = json.loads(request.body.decode('utf-8'))
                        request_body = self._mask_sensitive_data(request_body)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    request_body = {'_raw': '[Binary or invalid JSON]'}
            
            tenant_id = None
            if hasattr(request, 'user') and request.user.is_authenticated and hasattr(request.user, 'tenant') and request.user.tenant:
                tenant_id = str(request.user.tenant.id)
            
            log_data = {
                'event': 'request',
                'correlation_id': getattr(request, 'correlation_id', 'unknown'),
                'method': request.method,
                'path': request.path,
                'query_params': dict(request.GET),
                'ip': self._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'tenant_id': tenant_id,
                'user_id': str(request.user.id) if (hasattr(request, 'user') and request.user.is_authenticated) else None,
                'request_body': request_body if request_body else None,
            }
            
            # Prefer JSON logging if possible, otherwise string
            self._emit_log(log_data, 'info')
        except Exception as e:
            # Fallback logging if something goes wrong
            logger.error(f"Error logging request: {str(e)}", extra={
                'correlation_id': getattr(request, 'correlation_id', 'unknown'),
                'path': request.path
            })
    
    def _log_response(self, request, response, duration):
        """Log outgoing response with duration."""
        try:
            # Get response data (only for JSON responses and non-2xx statuses)
            response_data = None
            if response.status_code >= 400 and hasattr(response, 'content'):
                try:
                    if response.get('Content-Type', '').startswith('application/json'):
                        response_data = json.loads(response.content.decode('utf-8'))
                        response_data = self._mask_sensitive_data(response_data)
                except (json.JSONDecodeError, UnicodeDecodeError, AttributeError):
                    pass
            
            tenant_id = None
            if hasattr(request, 'user') and request.user.is_authenticated and hasattr(request.user, 'tenant') and request.user.tenant:
                tenant_id = str(request.user.tenant.id)
            
            log_data = {
                'event': 'response',
                'correlation_id': getattr(request, 'correlation_id', 'unknown'),
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration_ms': round(duration, 2),
                'tenant_id': tenant_id,
                'user_id': str(request.user.id) if (hasattr(request, 'user') and request.user.is_authenticated) else None,
                'response_data': response_data if response_data else None,
            }
            
            # Use appropriate log level
            level = 'info'
            if response.status_code >= 500:
                level = 'error'
            elif response.status_code >= 400:
                level = 'warning'
                
            self._emit_log(log_data, level)
        except Exception as e:
            logger.error(f"Error logging response: {str(e)}", extra={
                'correlation_id': getattr(request, 'correlation_id', 'unknown'),
                'path': request.path
            })

    def _emit_log(self, data, level):
        """Helper to emit log either as JSON or as structured attributes."""
        level_func = getattr(logger, level.lower())
        try:
            # We log as simple string because the 'json' formatter in LOGGING 
            # will handle converting the record to JSON if it's active.
            # If we dump to JSON here, and the formatter also dumps to JSON, 
            # we get double encoded JSON.
            level_func(f"{data['event'].upper()}: {data['method']} {data['path']} - {data.get('status_code', '')}", extra=data)
        except Exception:
            # Fallback to pure string
            level_func(json.dumps(data))
    
    def _mask_sensitive_data(self, data):
        """Recursively mask sensitive data in dictionaries."""
        if isinstance(data, dict):
            return {
                key: '***MASKED***' if key.lower() in self.SENSITIVE_KEYS else self._mask_sensitive_data(value)
                for key, value in data.items()
            }
        elif isinstance(data, list):
            return [self._mask_sensitive_data(item) for item in data]
        else:
            return data
    
    def _get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '')
        return ip
