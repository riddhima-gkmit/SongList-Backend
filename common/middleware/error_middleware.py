from http import HTTPStatus
from django.http import JsonResponse
import json


class JSONErrorMiddleware:
    """
    Middleware to convert error responses to JSON format.
    
    Handles HTTP errors (4xx, 5xx) and returns consistent JSON responses
    instead of Django's default HTML error pages.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # User-friendly error messages for common status codes
        self.user_friendly_messages = {
            400: "Bad request. Please check your input and try again.",
            401: "Authentication required. Please log in to access this resource.",
            403: "You don't have permission to access this resource.",
            404: "The requested resource was not found. Please check the URL and try again.",
            405: "This method is not allowed for this resource.",
            406: "The requested format is not supported.",
            408: "Request timeout. Please try again.",
            409: "A conflict occurred. The resource may have been modified.",
            410: "This resource is no longer available.",
            413: "The request is too large. Please reduce the payload size.",
            414: "The request URL is too long.",
            415: "The media type is not supported.",
            422: "The request was well-formed but contains semantic errors.",
            429: "Too many requests. Please try again later.",
            500: "An internal server error occurred. Please try again later or contact support.",
            501: "This feature is not implemented.",
            502: "Bad gateway. The server received an invalid response.",
            503: "Service temporarily unavailable. Please try again later.",
            504: "Gateway timeout. The server did not respond in time.",
        }

    def __call__(self, request):
        response = self.get_response(request)

        status_code = response.status_code
        # Check if response is an error status (400-599)
        if not (HTTPStatus.BAD_REQUEST.value <= status_code <= HTTPStatus.INTERNAL_SERVER_ERROR.value):
            return response

        # If response is already JSON (from DRF exception handler), don't override it
        content_type = response.get('Content-Type', '')
        if 'application/json' in content_type:
            try:
                # Try to parse existing JSON response
                if hasattr(response, 'content'):
                    json.loads(response.content)
                    # If it's already valid JSON, return as-is
                    return response
            except (json.JSONDecodeError, TypeError, AttributeError):
                # If parsing fails, continue to convert it
                pass

        # Get user-friendly message
        message = self.user_friendly_messages.get(
            status_code,
            f"An error occurred (HTTP {status_code})"
        )

        # Try to extract useful information from response content if it's text
        error_detail = None
        if hasattr(response, 'content'):
            try:
                content = response.content.decode('utf-8')
                # If it's HTML, provide generic message
                if '<html' in content.lower() or '<body' in content.lower():
                    error_detail = "The requested resource was not found or is unavailable."
                else:
                    # Try to extract meaningful text (first 200 chars)
                    error_detail = content[:200].strip()
                    if not error_detail:
                        error_detail = None
            except (UnicodeDecodeError, AttributeError):
                pass

        # Return a JSON error response for 4xx and 5xx errors
        # Format matches exception_handler for consistency
        error_data = {
            "status": "error",
            "message": message,
            "errors": {
                "detail": error_detail if error_detail else message
            }
        }
        
        error_response = JsonResponse(error_data)
        error_response.status_code = status_code
        return error_response
