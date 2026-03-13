"""Token denylist middleware."""
from django.http import JsonResponse


class TokenDenylistMiddleware:
    """Check if access token is denylisted."""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth_header = request.META.get("HTTP_AUTHORIZATION")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            from django.core.cache import cache

            if cache.get(f"denylist_{token}"):
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Token has been denylisted. Please login again.",
                        "errors": {"detail": "This session is no longer valid."},
                    },
                    status=401,
                )

        return self.get_response(request)
