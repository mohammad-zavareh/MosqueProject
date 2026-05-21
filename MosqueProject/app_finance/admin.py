from django.contrib import admin
from django.utils.html import format_html
from .models import *


class FinanceBaseAdmin(admin.ModelAdmin):

    readonly_fields = (
        'created_at',
        'updated_at',
        'created_by',
        'updated_by',
        'deleted_at',
        'deleted_by',
    )

    save_on_top = True

    list_per_page = 30

    actions = ['soft_delete_selected']

    fieldsets = (
        ('اطلاعات سیستمی', {
            'classes': ('collapse',),
            'fields': (
                'created_at',
                'updated_at',
                'created_by',
                'updated_by',
                'is_deleted',
                'deleted_at',
                'deleted_by',
            )
        }),
    )

    def save_model(self, request, obj, form, change):

        if not obj.pk:
            obj.created_by = request.user

        obj.updated_by = request.user

        super().save_model(request, obj, form, change)

    @admin.action(description='حذف نرم انتخاب شده‌ها')
    def soft_delete_selected(self, request, queryset):

        for obj in queryset:
            obj.soft_delete(user=request.user)


@admin.register(Event)
class EventAdmin(FinanceBaseAdmin):

    list_display = (
        'id',
        'name',
        'description_short',
        'is_deleted',
        'created_at',
    )

    search_fields = (
        'name',
        'description',
    )

    ordering = (
        'name',
    )

    fieldsets = (
        ('اطلاعات مناسبت', {
            'fields': (
                'name',
                'description',
            )
        }),
    ) + FinanceBaseAdmin.fieldsets

    def description_short(self, obj):

        if obj.description:
            return obj.description[:50]

        return '-'

    description_short.short_description = 'توضیحات'


# =========================
# Fund
# =========================

@admin.register(Fund)
class FundAdmin(FinanceBaseAdmin):

    list_display = (
        'id',
        'name',
        'description_short',
        'is_deleted',
        'created_at',
    )

    search_fields = (
        'name',
        'description',
    )

    ordering = ('name',)

    fieldsets = (
        ('اطلاعات صندوق', {
            'fields': (
                'name',
                'description',
            )
        }),
    ) + FinanceBaseAdmin.fieldsets

    def description_short(self, obj):
        return obj.description[:50]

    description_short.short_description = 'توضیحات'


# =========================
# Income Category
# =========================

@admin.register(IncomeCategory)
class IncomeCategoryAdmin(FinanceBaseAdmin):

    list_display = (
        'id',
        'name',
        'parent',
        'children_count',
    )

    search_fields = (
        'name',
    )

    list_filter = (
        'parent',
    )

    autocomplete_fields = (
        'parent',
    )

    fieldsets = (
        ('دسته بندی درآمد', {
            'fields': (
                'name',
                'parent',
            )
        }),
    ) + FinanceBaseAdmin.fieldsets

    def children_count(self, obj):
        return obj.children.count()

    children_count.short_description = 'تعداد زیرمجموعه'


# =========================
# Expense Category
# =========================

@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(FinanceBaseAdmin):

    list_display = (
        'id',
        'name',
        'parent',
        'children_count',
    )

    search_fields = (
        'name',
    )

    list_filter = (
        'parent',
    )

    autocomplete_fields = (
        'parent',
    )

    fieldsets = (
        ('دسته بندی هزینه', {
            'fields': (
                'name',
                'parent',
            )
        }),
    ) + FinanceBaseAdmin.fieldsets

    def children_count(self, obj):
        return obj.children.count()

    children_count.short_description = 'تعداد زیرمجموعه'


# =========================
# Inline Details
# =========================

class IncomeDetailInline(admin.StackedInline):

    model = IncomeDetail
    extra = 0
    autocomplete_fields = ('category',)


class ExpenseDetailInline(admin.StackedInline):

    model = ExpenseDetail
    extra = 0
    autocomplete_fields = ('category',)



# =========================
# Financial Transaction
# =========================

@admin.register(FinancialTransaction)
class FinancialTransactionAdmin(FinanceBaseAdmin):

    list_display = (
        'id',
        'transaction_type_badge',
        'amount',
        'fund',
        'date',
        'reference_number',
        'is_deleted',
    )

    list_filter = (
        'transaction_type',
        'fund',
        'date',
        'is_deleted',
    )

    search_fields = (
        'description',
        'reference_number',
    )

    date_hierarchy = 'date'

    autocomplete_fields = (
        'fund',
    )

    readonly_fields = FinanceBaseAdmin.readonly_fields + (
        'amount_colored',
    )

    fieldsets = (
        ('اطلاعات تراکنش', {
            'fields': (
                'transaction_type',
                'amount',
                'amount_colored',
                'fund',
                'date',
                'reference_number',
                'description',
            )
        }),
    ) + FinanceBaseAdmin.fieldsets

    def get_inline_instances(self, request, obj=None):

        if not obj:
            return []

        inlines = []

        if obj.transaction_type == 'INCOME':
            inlines.append(IncomeDetailInline(self.model, self.admin_site))

        elif obj.transaction_type == 'EXPENSE':
            inlines.append(ExpenseDetailInline(self.model, self.admin_site))

        return inlines

    def transaction_type_badge(self, obj):

        colors = {
            'INCOME': 'green',
            'EXPENSE': 'red',
            'TRANSFER': 'blue',
        }

        return format_html(
            '<span style="color:white;background:{};padding:4px 8px;border-radius:8px;">{}</span>',
            colors.get(obj.transaction_type),
            obj.get_transaction_type_display()
        )

    transaction_type_badge.short_description = 'نوع تراکنش'

    def amount_colored(self, obj):

        color = 'green'

        if obj.transaction_type == 'EXPENSE':
            color = 'red'

        return format_html(
            '<strong style="color:{};">{:,.0f}</strong>',
            color,
            obj.amount
        )

    amount_colored.short_description = 'مبلغ'


# =========================
# Income Detail
# =========================

@admin.register(IncomeDetail)
class IncomeDetailAdmin(FinanceBaseAdmin):

    list_display = (
        'id',
        'transaction',
        'category',
        'payer_name',
    )

    list_filter = (
        'category',
    )

    search_fields = (
        'payer_name',
    )

    autocomplete_fields = (
        'transaction',
        'category',
    )

    fieldsets = (
        ('جزئیات درآمد', {
            'fields': (
                'transaction',
                'category',
                'payer_name',
            )
        }),
    ) + FinanceBaseAdmin.fieldsets


# =========================
# Expense Detail
# =========================

@admin.register(ExpenseDetail)
class ExpenseDetailAdmin(FinanceBaseAdmin):

    list_display = (
        'id',
        'transaction',
        'category',
        'vendor_name',
    )

    list_filter = (
        'category',
    )

    search_fields = (
        'vendor_name',
    )

    autocomplete_fields = (
        'transaction',
        'category',
    )

    fieldsets = (
        ('جزئیات هزینه', {
            'fields': (
                'transaction',
                'category',
                'vendor_name',
            )
        }),
    ) + FinanceBaseAdmin.fieldsets


