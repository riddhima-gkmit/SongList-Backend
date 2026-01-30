"""
Thread-local context management for request lifecycle.

This module manages context variables that need to be accessible
across the request lifecycle (middleware, views, logging, etc).
"""

from contextvars import ContextVar

correlation_id_var = ContextVar("correlation_id", default=None)
current_tenant = ContextVar("tenant", default=None)


def get_correlation_id():
    """
    Get the current correlation ID from context.
    """
    return correlation_id_var.get()


def set_correlation_id(correlation_id):
    """
    Set the correlation ID in context.
    """
    correlation_id_var.set(correlation_id)
