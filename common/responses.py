"""
Standardized API response utilities.

All API responses use these helpers for consistency.
"""
from rest_framework.response import Response
from rest_framework import status


def success_response(message: str, data=None, status_code=status.HTTP_200_OK):
    """
    Create a success response.

    Args:
        message: Human-readable success message
        data: Response data (dict, list, or None)
        status_code: HTTP status code

    Returns:
        Response with format: {"status": "success", "message": "...", "data": {...}}
    """
    response_data = {
        "status": "success",
        "message": message,
    }
    if data is not None:
        response_data["data"] = data
    return Response(response_data, status=status_code)


def error_response(message: str, errors=None, status_code=status.HTTP_400_BAD_REQUEST):
    """
    Create an error response.

    Args:
        message: Human-readable error message
        errors: Error details (dict or string)
        status_code: HTTP status code

    Returns:
        Response with format: {"status": "error", "message": "...", "errors": {...}}
    """
    response_data = {
        "status": "error",
        "message": message,
    }
    if errors is not None:
        if isinstance(errors, str):
            response_data["errors"] = {"detail": errors}
        else:
            response_data["errors"] = errors
    return Response(response_data, status=status_code)
