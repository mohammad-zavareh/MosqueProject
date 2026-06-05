# app_core/mixins.py
# ─────────────────────────────────────────────────────────
# این mixin را به ویوهایی که می‌خوای حسابرسی بشن اضافه کن
# ─────────────────────────────────────────────────────────

from .models import AuditLog, log_action


# ── فیلدهایی که نباید لاگ بشن ─────────────────────────
EXCLUDED_FIELDS = {
    "created_at", "updated_at", "created_by", "updated_by",
    "deleted_at", "deleted_by", "is_deleted", "password",
}


def _get_instance_data(instance):
    """مقادیر فعلی فیلدهای یک instance رو برمی‌گردونه."""
    data = {}
    for field in instance._meta.concrete_fields:
        if field.name in EXCLUDED_FIELDS:
            continue
        try:
            value = getattr(instance, field.name)
            # FK رو به pk تبدیل کن
            if hasattr(value, "pk"):
                value = str(value)
            data[field.name] = str(value) if value is not None else None
        except Exception:
            pass
    return data


def _compute_changes(before: dict, after: dict) -> dict:
    """تفاوت دو dict رو پیدا می‌کنه."""
    changes = {}
    all_keys = set(before.keys()) | set(after.keys())
    for key in all_keys:
        b = before.get(key)
        a = after.get(key)
        if b != a:
            changes[key] = {"before": b, "after": a}
    return changes


class AuditViewMixin:
    """
    به ویوهای Create و Update اضافه کن.

    class IncomeCreateView(AuditViewMixin, LoginRequiredMixin, TemplateView):
        ...
    """

    def _log_create(self, request, instance):
        log_action(
            user     = request.user,
            action   = AuditLog.ACTION_CREATE,
            instance = instance,
            changes  = {"_new": _get_instance_data(instance)},
            request  = request,
        )

    def _log_update(self, request, instance, before_data: dict):
        after_data = _get_instance_data(instance)
        changes    = _compute_changes(before_data, after_data)
        if changes:
            log_action(
                user     = request.user,
                action   = AuditLog.ACTION_UPDATE,
                instance = instance,
                changes  = changes,
                request  = request,
            )

    def _log_delete(self, request, instance):
        log_action(
            user     = request.user,
            action   = AuditLog.ACTION_DELETE,
            instance = instance,
            request  = request,
        )

    def _snapshot(self, instance) -> dict:
        """قبل از save، snapshot بگیر."""
        return _get_instance_data(instance)
