# inventory/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import *


# =========================
# Base Admin
# =========================

class InventoryBaseAdmin(admin.ModelAdmin):
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


# =========================
# Supplier
# =========================

@admin.register(Supplier)
class SupplierAdmin(InventoryBaseAdmin):
    list_display = (
        'id',
        'name',
        'phone',
        'is_deleted',
    )

    search_fields = (
        'name',
        'phone',
        'address',
    )

    fieldsets = (
                    ('اطلاعات تامین کننده', {
                        'fields': (
                            'name',
                            'phone',
                            'address',
                        )
                    }),
                ) + InventoryBaseAdmin.fieldsets


# =========================
# Inventory Category
# =========================

@admin.register(InventoryCategory)
class InventoryCategoryAdmin(InventoryBaseAdmin):
    list_display = (
        'id',
        'name',
    )

    search_fields = (
        'name',
    )

    fieldsets = (
                    ('دسته بندی انبار', {
                        'fields': (
                            'name',
                        )
                    }),
                ) + InventoryBaseAdmin.fieldsets



# =========================
# Inventory Item
# =========================

class InventoryTransactionInline(admin.TabularInline):
    model = InventoryTransaction
    extra = 0

    autocomplete_fields = (
        'expense',
    )


@admin.register(InventoryItem)
class InventoryItemAdmin(InventoryBaseAdmin):
    list_display = (
        'id',
        'name',
        'category',
        'unit',
        'stock_status',
        'purchase_price',
        'supplier',
    )

    list_filter = (
        'category',
        'supplier',
    )

    search_fields = (
        'name',
    )

    autocomplete_fields = (
        'category',
        'supplier',
    )

    inlines = [
        InventoryTransactionInline
    ]

    fieldsets = (
                    ('اطلاعات کالا', {
                        'fields': (
                            'name',
                            'category',
                            'unit',
                            'current_stock',
                            'purchase_price',
                            'supplier',
                        )
                    }),
                ) + InventoryBaseAdmin.fieldsets

    def stock_status(self, obj):
        color = 'green'

        if obj.current_stock <= 0:
            color = 'red'

        return format_html(
            '<strong style="color:{};">{}</strong>',
            color,
            obj.current_stock
        )

    stock_status.short_description = 'موجودی'


# =========================
# Inventory Transaction
# =========================

@admin.register(InventoryTransaction)
class InventoryTransactionAdmin(InventoryBaseAdmin):
    list_display = (
        'id',
        'item',
        'transaction_type_badge',
        'quantity',
        'unit_price',
        'total_price_colored',
        'date',
    )

    list_filter = (
        'transaction_type',
        'date',
    )

    search_fields = (
        'item__name',
        'notes',
    )

    autocomplete_fields = (
        'item',
        'expense',
    )

    readonly_fields = (
                          'total_price',
                      ) + InventoryBaseAdmin.readonly_fields

    date_hierarchy = 'date'

    fieldsets = (
                    ('اطلاعات تراکنش انبار', {
                        'fields': (
                            'item',
                            'transaction_type',
                            'quantity',
                            'unit_price',
                            'total_price',
                            'date',
                            'expense',
                            'notes',
                        )
                    }),
                ) + InventoryBaseAdmin.fieldsets

    def transaction_type_badge(self, obj):
        colors = {
            'PURCHASE': 'green',
            'USAGE': 'orange',
            'ADJUSTMENT': 'blue',
        }

        return format_html(
            '<span style="background:{};color:white;padding:4px 8px;border-radius:8px;">{}</span>',
            colors.get(obj.transaction_type),
            obj.get_transaction_type_display()
        )

    transaction_type_badge.short_description = 'نوع عملیات'

    def total_price_colored(self, obj):
        return format_html(
            '<strong style="color:green;">{:,.0f}</strong>',
            obj.total_price
        )

    total_price_colored.short_description = 'مبلغ کل'
