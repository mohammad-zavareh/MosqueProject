from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

User = get_user_model()


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditModel(models.Model):
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_%(class)s_set"
    )

    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_%(class)s_set"
    )

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)

    deleted_at = models.DateTimeField(
        null=True,
        blank=True
    )

    deleted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_%(class)s_set"
    )

    class Meta:
        abstract = True

    def soft_delete(self, user=None):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.deleted_by = user
        self.save()


class BaseModel(
    TimeStampedModel,
    AuditModel,
    SoftDeleteModel
):
    class Meta:
        abstract = True



class AuditLog(models.Model):

    ACTION_CREATE = "CREATE"
    ACTION_UPDATE = "UPDATE"
    ACTION_DELETE = "DELETE"

    ACTION_CHOICES = [
        (ACTION_CREATE, "ایجاد"),
        (ACTION_UPDATE, "ویرایش"),
        (ACTION_DELETE, "حذف"),
    ]

    # ── کاربر ──────────────────────────────────────────
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name="کاربر",
    )

    # ── نوع عملیات ─────────────────────────────────────
    action = models.CharField(
        max_length=10,
        choices=ACTION_CHOICES,
        verbose_name="عملیات",
    )

    # ── مدل هدف (Generic FK) ───────────────────────────
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name="نوع مدل",
    )
    object_id = models.PositiveIntegerField(
        verbose_name="شناسه رکورد",
    )
    content_object = GenericForeignKey("content_type", "object_id")

    # ── نام قابل خواندن مدل و رکورد ────────────────────
    model_name  = models.CharField(max_length=100, verbose_name="مدل")
    object_repr = models.CharField(max_length=255, verbose_name="رکورد", blank=True)

    # ── تغییرات (JSON) ──────────────────────────────────
    # {"field_name": {"before": "...", "after": "..."}, ...}
    changes = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="تغییرات",
    )

    # ── زمان ───────────────────────────────────────────
    timestamp = models.DateTimeField(
        default=timezone.now,
        verbose_name="زمان",
        db_index=True,
    )

    # ── IP ─────────────────────────────────────────────
    ip_address = models.GenericIPAddressField(
        null=True, blank=True,
        verbose_name="آدرس IP",
    )

    class Meta:
        verbose_name          = "لاگ حسابرسی"
        verbose_name_plural   = "لاگ‌های حسابرسی"
        ordering              = ["-timestamp"]

    def __str__(self):
        return f"{self.get_action_display()} — {self.model_name} #{self.object_id}"


# ─────────────────────────────────────────────────────────
#  تابع کمکی برای ثبت لاگ
# ─────────────────────────────────────────────────────────

def log_action(user, action, instance, changes=None, request=None):
    """
    هر جا save_model یا view ذخیره می‌کند صدا بزن.

    مثال در view:
        from app_core.models import AuditLog, log_action
        log_action(request.user, AuditLog.ACTION_UPDATE, obj,
                   changes={"amount": {"before": 100, "after": 200}},
                   request=request)
    """
    ct = ContentType.objects.get_for_model(instance)
    ip = None
    if request:
        x_forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        ip = x_forwarded.split(",")[0] if x_forwarded else request.META.get("REMOTE_ADDR")

    AuditLog.objects.create(
        user         = user,
        action       = action,
        content_type = ct,
        object_id    = instance.pk,
        model_name   = ct.model,
        object_repr  = str(instance)[:255],
        changes      = changes or {},
        ip_address   = ip,
    )
