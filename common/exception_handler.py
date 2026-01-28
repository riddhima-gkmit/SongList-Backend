"""
Custom exception handler for consistent API error responses.

Ensures all errors return JSON, never HTML.
"""
from rest_framework.views import exception_handler
from rest_framework.exceptions import (
    ValidationError,
    NotFound,
    PermissionDenied,
    AuthenticationFailed,
    NotAuthenticated,
    APIException,
)
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from django.core.exceptions import ObjectDoesNotExist


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns consistent JSON responses.

    Response format:
    {
        "status": "error",
        "message": "Human readable message",
        "errors": {...}
    }
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        custom_response = {
            "status": "error",
            "message": get_error_message(exc),
            "errors": format_errors(response.data),
        }
        response.data = custom_response
        return response

    # Handle non-DRF exceptions
    if isinstance(exc, Http404) or isinstance(exc, ObjectDoesNotExist):
        message = "Resource not found"
        if isinstance(exc, ObjectDoesNotExist):
            msg = str(exc)
            if " matching query" in msg:
                # e.g., "User matching query does not exist." -> "User not found"
                message = msg.split(" matching query")[0] + " not found"
        
        return create_error_response(
            message=message,
            errors={"detail": str(exc) if str(exc) else "The requested resource was not found"},
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # Handle unexpected exceptions (500 errors)
    return create_error_response(
        "Internal server error",
        {"detail": "An unexpected error occurred. Please try again later."},
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


def get_error_message(exc):
    """Get human-readable error message from exception."""
    if isinstance(exc, ValidationError):
        # Handle dict or list details
        detail = exc.detail
        if isinstance(detail, dict):
            # Get first error from dict values
            first_field = next(iter(detail))
            first_error = detail[first_field]
            if isinstance(first_error, list):
                return str(first_error[0])
            return str(first_error)
        elif isinstance(detail, list):
            return str(detail[0])
        return str(detail)
    if isinstance(exc, NotFound):
        return "Resource not found"
    if isinstance(exc, ObjectDoesNotExist):
        msg = str(exc)
        if " matching query" in msg:
            return msg.split(" matching query")[0] + " not found"
        return "Resource not found"
    if isinstance(exc, PermissionDenied):
        return "Permission denied"
    if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        return "Authentication required"
    if isinstance(exc, APIException):
        return str(exc.detail) if hasattr(exc, "detail") else "Request failed"
    return "Request failed"


def format_errors(data):
    """
    Format error data consistently and ensure all values are strings.
    Handles nested dictionaries and lists (common in DRF validation errors).
    """
    if isinstance(data, dict):
        return {key: format_errors(value) for key, value in data.items()}
    if isinstance(data, list):
        # Flatten single-item lists if they contain strings
        if len(data) == 1:
            return format_errors(data[0])
        return [format_errors(item) for item in data]
    
    # Convert DRF ErrorDetail or other objects to plain strings
    return str(data)


def create_error_response(message, errors, status_code):
    """Create a Response object for errors."""
    return Response(
        {
            "status": "error",
            "message": message,
            "errors": errors,
        },
        status=status_code,
    )
