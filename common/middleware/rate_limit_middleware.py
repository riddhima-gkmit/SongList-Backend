"""
Rate limiting middleware for authentication endpoints.
"""
from django.core.cache import cache
from django.http import JsonResponse
from django.conf import settings
import time


class RateLimitMiddleware:
    """
    Simple rate limiting middleware using Django cache.
    Limits login attempts per IP address.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = getattr(settings, 'RATE_LIMIT_ENABLE', True)
        self.max_attempts = getattr(settings, 'RATE_LIMIT_LOGIN_ATTEMPTS', 5)
        self.window = getattr(settings, 'RATE_LIMIT_LOGIN_WINDOW', 300)  # 5 minutes

    def __call__(self, request):
        if not self.enabled:
            return self.get_response(request)
        
        # Only rate limit POST requests to login endpoint
        if request.method == 'POST' and not request.user.is_authenticated:
            ip_address = self.get_client_ip(request)
            cache_key = f'rate_limit:login:{ip_address}'
            
            # Get current attempts
            attempts = cache.get(cache_key, {'count': 0, 'reset_time': time.time() + self.window})
            
            # Check if window has expired
            if time.time() > attempts['reset_time']:
                attempts = {'count': 0, 'reset_time': time.time() + self.window}
            
            # Check if rate limit exceeded
            if attempts['count'] >= self.max_attempts:
                retry_after = int(attempts['reset_time'] - time.time())
                return JsonResponse({
                    'status': 'error',
                    'message': f'Too many login attempts. Please try again in {retry_after} seconds.',
                    'retry_after': retry_after
                }, status=429)
            
            # Increment attempts
            attempts['count'] += 1
            cache.set(cache_key, attempts, timeout=self.window)
        
        response = self.get_response(request)
        
        # Clear rate limit on successful login
        if request.method == 'POST' and '/auth/login/' in request.path and response.status_code == 200:
            ip_address = self.get_client_ip(request)
            cache_key = f'rate_limit:login:{ip_address}'
            cache.delete(cache_key)
        
        return response
    
    def get_client_ip(self, request):
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
