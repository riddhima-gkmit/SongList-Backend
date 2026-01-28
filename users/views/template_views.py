"""
Template views for password reset and email verification UI.
"""
from django.shortcuts import render
from django.views import View


class ForgotPasswordView(View):
    """Render the forgot password template."""
    template_name = 'users/forgot_password.html'
    
    def get(self, request):
        """Display the forgot password form."""
        return render(request, self.template_name)


class VerifyEmailView(View):
    """Render the email verification template."""
    template_name = 'users/verify_email.html'
    
    def get(self, request):
        """Display the email verification form."""
        return render(request, self.template_name)
