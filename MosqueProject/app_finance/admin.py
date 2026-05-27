from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum

from .models import (
    Fund,
    Event,
    IncomeCategory,
    ExpenseCategory,
    FinancialTransaction,
    IncomeDetail,
    ExpenseDetail,
)


# ══════════════════════════════════════════════════════════════
#  BaseModelAdmin
# ══════════════════════════════════════════════════════════════

class BaseModelAdmin(admin.ModelAdmin):

    readonly_fields = (
        "created_at", "updated_at",
        "created_by", "updated_by",
        "deleted_at", "deleted_by",
    )

    audit_fieldset = (
        "اطلاعات سیستمی", {
            "fields": (
                ("created_at", "created_by"),
                ("updated_at", "updated_by"),
                ("is_deleted", "deleted_at", "deleted_by"),
            ),
            "classes": ("collapse",),
        }
    )

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_deleted=False)

    def save_model(self, request, obj, form, change):
        if not change and not obj.created_by_id:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    # ── ستون‌های مشترک ──────────────────────────────────────
    def created_fa(self, obj):
        if obj.created_at:
            return format_html(
                '<span style="font-size:12px;color:#64748b">{}</span>',
                obj.created_at.strftime("%Y/%m/%d %H:%M"),
            )
        return "—"
    created_fa.short_description = "تاریخ ایجاد"
    created_fa.admin_order_field = "created_at"

    def updated_fa(self, obj):
        if obj.updated_at:
            return format_html(
                '<span style="font-size:12px;color:#64748b">{}</span>',
                obj.updated_at.strftime("%Y/%m/%d %H:%M"),
            )
        return "—"
    updated_fa.short_description = "آخرین ویرایش"
    updated_fa.admin_order_field = "updated_at"

    def created_by_display(self, obj):
        u = obj.created_by
        if not u:
            return "—"
        return u.get_full_name() or u.username
    created_by_display.short_description = "ایجادکننده"

    def updated_by_display(self, obj):
        u = obj.updated_by
        if not u:
            return "—"
        return u.get_full_name() or u.username
    updated_by_display.short_description = "ویرایش‌کننده"


# ══════════════════════════════════════════════════════════════
#  صندوق  (Fund)
# ══════════════════════════════════════════════════════════════

@admin.register(Fund)
class FundAdmin(BaseModelAdmin):
    list_display = (
        "name", "transaction_count",
        "total_income", "total_expense",
        "created_by_display", "created_fa",
    )
    search_fields = ("name", "description")
    ordering      = ("name",)
    readonly_fields = BaseModelAdmin.readonly_fields + (
        "transaction_count", "total_income", "total_expense",
    )
    fieldsets = (
        ("اطلاعات صندوق", {
            "fields": ("name", "description"),
        }),
        ("آمار", {
            "fields": ("transaction_count", "total_income", "total_expense"),
            "classes": ("collapse",),
        }),
        BaseModelAdmin.audit_fieldset,
    )

    def transaction_count(self, obj):
        return obj.transactions.filter(is_deleted=False).count()
    transaction_count.short_description = "تعداد تراکنش"

    def total_income(self, obj):
        total = (
            obj.transactions
            .filter(transaction_type="INCOME", is_deleted=False)
            .aggregate(s=Sum("amount"))["s"] or 0
        )
        return format_html(
            '<span style="color:#16a34a;font-weight:700">{} تومان</span>',
            "{:,.0f}".format(total),
        )
    total_income.short_description = "جمع درآمد"

    def total_expense(self, obj):
        total = (
            obj.transactions
            .filter(transaction_type="EXPENSE", is_deleted=False)
            .aggregate(s=Sum("amount"))["s"] or 0
        )
        return format_html(
            '<span style="color:#dc2626;font-weight:700">{} تومان</span>',
            "{:,.0f}".format(total),
        )
    total_expense.short_description = "جمع هزینه"


# ══════════════════════════════════════════════════════════════
#  مناسبت  (Event)
# ══════════════════════════════════════════════════════════════

@admin.register(Event)
class EventAdmin(BaseModelAdmin):
    list_display  = (
        "name", "transaction_count",
        "created_by_display", "created_fa",
    )
    search_fields = ("name", "description")
    ordering      = ("name",)
    fieldsets = (
        ("اطلاعات مناسبت", {
            "fields": ("name", "description"),
        }),
        BaseModelAdmin.audit_fieldset,
    )

    def transaction_count(self, obj):
        return obj.financialtransaction_set.filter(is_deleted=False).count()
    transaction_count.short_description = "تعداد تراکنش"


# ══════════════════════════════════════════════════════════════
#  دسته‌بندی درآمد  (IncomeCategory)
# ══════════════════════════════════════════════════════════════

@admin.register(IncomeCategory)
class IncomeCategoryAdmin(BaseModelAdmin):
    list_display  = (
        "name", "parent", "children_count",
        "income_count", "created_fa",
    )
    list_filter   = ("parent",)
    search_fields = ("name",)
    ordering      = ("parent__name", "name")
    raw_id_fields = ("parent",)
    fieldsets = (
        ("اطلاعات دسته‌بندی", {
            "fields": ("name", "parent"),
        }),
        BaseModelAdmin.audit_fieldset,
    )

    def children_count(self, obj):
        count = obj.children.filter(is_deleted=False).count()
        return count if count else "—"
    children_count.short_description = "زیردسته"

    def income_count(self, obj):
        return obj.incomes.filter(is_deleted=False).count()
    income_count.short_description = "تعداد درآمد"


# ══════════════════════════════════════════════════════════════
#  دسته‌بندی هزینه  (ExpenseCategory)
# ══════════════════════════════════════════════════════════════

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(BaseModelAdmin):
    list_display  = (
        "name", "parent", "children_count",
        "expense_count", "created_fa",
    )
    list_filter   = ("parent",)
    search_fields = ("name",)
    ordering      = ("parent__name", "name")
    raw_id_fields = ("parent",)
    fieldsets = (
        ("اطلاعات دسته‌بندی", {
            "fields": ("name", "parent"),
        }),
        BaseModelAdmin.audit_fieldset,
    )

    def children_count(self, obj):
        count = obj.children.filter(is_deleted=False).count()
        return count if count else "—"
    children_count.short_description = "زیردسته"

    def expense_count(self, obj):
        return obj.expenses.filter(is_deleted=False).count()
    expense_count.short_description = "تعداد هزینه"


# ══════════════════════════════════════════════════════════════
#  Inline های Detail
# ══════════════════════════════════════════════════════════════

class IncomeDetailInline(admin.StackedInline):
    model               = IncomeDetail
    extra               = 0
    max_num             = 1
    can_delete          = False
    verbose_name        = "جزئیات درآمد"
    verbose_name_plural = "جزئیات درآمد"
    fields              = ("category", "payer_name")
    autocomplete_fields = ("category",)
    readonly_fields     = BaseModelAdmin.readonly_fields

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_deleted=False)


class ExpenseDetailInline(admin.StackedInline):
    model               = ExpenseDetail
    extra               = 0
    max_num             = 1
    can_delete          = False
    verbose_name        = "جزئیات هزینه"
    verbose_name_plural = "جزئیات هزینه"
    fields              = ("category", "vendor_name")
    autocomplete_fields = ("category",)
    readonly_fields     = BaseModelAdmin.readonly_fields

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_deleted=False)


# ══════════════════════════════════════════════════════════════
#  تراکنش مالی  (FinancialTransaction)
# ══════════════════════════════════════════════════════════════

@admin.register(FinancialTransaction)
class FinancialTransactionAdmin(BaseModelAdmin):

    list_display = (
        "pk", "type_badge", "amount_colored",
        "date", "fund", "event",
        "reference_number", "receipt_thumb",
        "created_by_display", "created_fa",
    )
    list_filter = (
        "transaction_type",
        "fund",
        "event",
        "date",
    )
    search_fields = (
        "reference_number",
        "description",
        "fund__name",
        "event__name",
        "income_detail__payer_name",
        "income_detail__category__name",
        "expense_detail__vendor_name",
        "expense_detail__category__name",
    )
    date_hierarchy         = "date"
    ordering               = ("-date", "-created_at")
    list_per_page          = 25
    show_full_result_count = True

    readonly_fields = BaseModelAdmin.readonly_fields + (
        "type_badge",
        "receipt_preview",
    )
    autocomplete_fields = ("fund",)
    raw_id_fields       = ("event",)

    fieldsets = (
        ("اطلاعات اصلی", {
            "fields": (
                "transaction_type",
                ("amount", "date"),
                ("fund", "event"),
                "reference_number",
            ),
        }),
        ("توضیحات", {
            "fields": ("description",),
        }),
        ("تصویر رسید", {
            "fields": ("image_receipt", "receipt_preview"),
        }),
        BaseModelAdmin.audit_fieldset,
    )

    def get_inlines(self, request, obj=None):
        if obj is None:
            return []
        if obj.transaction_type == "INCOME":
            return [IncomeDetailInline]
        if obj.transaction_type == "EXPENSE":
            return [ExpenseDetailInline]
        return []

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related(
                "fund", "event",
                "created_by", "updated_by",
                "income_detail__category",
                "expense_detail__category",
            )
        )

    # ── ستون‌های لیست ───────────────────────────────────────
    def type_badge(self, obj):
        if obj.transaction_type == "INCOME":
            return format_html(
                '<span style="background:#dcfce7;color:#15803d;padding:2px 10px;'
                'border-radius:20px;font-size:12px;font-weight:700">{}</span>',
                "درآمد",
            )
        return format_html(
            '<span style="background:#fee2e2;color:#b91c1c;padding:2px 10px;'
            'border-radius:20px;font-size:12px;font-weight:700">{}</span>',
            "هزینه",
        )
    type_badge.short_description = "نوع"

    def amount_colored(self, obj):
        color = "#16a34a" if obj.transaction_type == "INCOME" else "#dc2626"
        sign  = "+"       if obj.transaction_type == "INCOME" else "-"
        return format_html(
            '<span style="color:{};font-weight:700">{}{}</span>',
            color,
            sign,
            "{:,.0f}".format(obj.amount),
        )
    amount_colored.short_description = "مبلغ"
    amount_colored.admin_order_field = "amount"

    def receipt_thumb(self, obj):
        if obj.image_receipt:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="width:48px;height:36px;'
                'object-fit:cover;border-radius:4px;border:1px solid #e2e8f0">'
                '</a>',
                obj.image_receipt.url,
                obj.image_receipt.url,
            )
        return "—"
    receipt_thumb.short_description = "رسید"

    def receipt_preview(self, obj):
        if obj.image_receipt:
            return format_html(
                '<a href="{}" target="_blank">'
                '<img src="{}" style="max-width:320px;max-height:240px;'
                'object-fit:contain;border-radius:8px;'
                'border:1px solid #e2e8f0;margin-top:6px">'
                '</a>',
                obj.image_receipt.url,
                obj.image_receipt.url,
            )
        return "رسیدی بارگذاری نشده"
    receipt_preview.short_description = "پیش‌نمایش رسید"


# ══════════════════════════════════════════════════════════════
#  جزئیات درآمد  (IncomeDetail)
# ══════════════════════════════════════════════════════════════

@admin.register(IncomeDetail)
class IncomeDetailAdmin(BaseModelAdmin):
    list_display  = (
        "transaction", "category", "payer_name",
        "amount_display", "created_by_display", "created_fa",
    )
    list_filter   = ("category",)
    search_fields = (
        "payer_name",
        "category__name",
        "transaction__reference_number",
    )
    raw_id_fields       = ("transaction",)
    autocomplete_fields = ("category",)
    ordering            = ("-created_at",)
    fieldsets = (
        ("اطلاعات درآمد", {
            "fields": ("transaction", "category", "payer_name"),
        }),
        BaseModelAdmin.audit_fieldset,
    )

    def amount_display(self, obj):
        return format_html(
            '<span style="color:#16a34a;font-weight:700">+{}</span>',
            "{:,.0f}".format(obj.transaction.amount),
        )
    amount_display.short_description = "مبلغ"
    amount_display.admin_order_field = "transaction__amount"

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related("transaction__fund", "category", "created_by")
        )


# ══════════════════════════════════════════════════════════════
#  جزئیات هزینه  (ExpenseDetail)
# ══════════════════════════════════════════════════════════════

@admin.register(ExpenseDetail)
class ExpenseDetailAdmin(BaseModelAdmin):
    list_display  = (
        "transaction", "category", "vendor_name",
        "amount_display", "created_by_display", "created_fa",
    )
    list_filter   = ("category",)
    search_fields = (
        "vendor_name",
        "category__name",
        "transaction__reference_number",
    )
    raw_id_fields       = ("transaction",)
    autocomplete_fields = ("category",)
    ordering            = ("-created_at",)
    fieldsets = (
        ("اطلاعات هزینه", {
            "fields": ("transaction", "category", "vendor_name"),
        }),
        BaseModelAdmin.audit_fieldset,
    )

    def amount_display(self, obj):
        return format_html(
            '<span style="color:#dc2626;font-weight:700">-{}</span>',
            "{:,.0f}".format(obj.transaction.amount),
        )
    amount_display.short_description = "مبلغ"
    amount_display.admin_order_field = "transaction__amount"

    def get_queryset(self, request):
        return (
            super().get_queryset(request)
            .select_related("transaction__fund", "category", "created_by")
        )
