import uuid
from django.db.models import Q


def parse_is_active(value):
    """Converts is_active query param to True/False. Returns None if not valid."""
    if value is None:
        return None
    v = str(value).strip().lower()
    if v in ("true", "1", "yes"):
        return True
    if v in ("false", "0", "no"):
        return False
    return None


def parse_tenant_ids(param_value):
    """Parses comma-separated tenant UUIDs. Returns (ids, None) on success or (None, error_msg) on fail."""
    if not param_value or not str(param_value).strip():
        return [], None
    parts = [tid.strip() for tid in str(param_value).split(",") if tid.strip()]
    result = []
    for tid in parts:
        try:
            result.append(uuid.UUID(tid))
        except ValueError:
            return None, f"Invalid tenant_id format: {tid}. Must be a valid UUID."
    return result, None


class UserListFilter:
    """Filters user list by is_active, name, email from query params."""

    def __init__(self, queryset, params):
        self.qs = queryset
        self.params = params if params is not None else {}

    def apply(self):
        self._filter_is_active()
        self._filter_name()
        self._filter_email()
        return self.qs

    def _filter_is_active(self):
        val = self.params.get("is_active")
        parsed = parse_is_active(val)
        if parsed is not None:
            self.qs = self.qs.filter(is_active=parsed)

    def _filter_name(self):
        name = (self.params.get("name") or "").strip()
        if not name:
            return
        self.qs = self.qs.filter(
            Q(username__icontains=name)
            | Q(first_name__icontains=name)
            | Q(last_name__icontains=name)
        )

    def _filter_email(self):
        email = (self.params.get("email") or "").strip()
        if not email:
            return
        self.qs = self.qs.filter(email__icontains=email)


class SuperAdminAdminsFilter(UserListFilter):
    """Same as UserListFilter but also filters by tenant_id (comma-separated UUIDs)."""

    def apply(self):
        tenant_ids, err = parse_tenant_ids(self.params.get("tenant_id"))
        if err is not None:
            raise ValueError(err)
        if tenant_ids:
            self.qs = self.qs.filter(tenant_id__in=tenant_ids)
        return super().apply()
