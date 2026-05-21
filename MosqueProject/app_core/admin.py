from django.contrib import admin

class BaseAdmin(admin.ModelAdmin):
    readonly_fields = (
        'created_at',
        'updated_at',
        'created_by',
        'updated_by',
        'deleted_at',
        'deleted_by',
    )

    list_filter = (
        'is_deleted',
        'created_at',
        'updated_at',
    )

    search_fields = ('id',)

    actions = ['soft_delete_selected', 'restore_selected']

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user

        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description='حذف نرم انتخاب شده‌ها')
    def soft_delete_selected(self, request, queryset):
        for obj in queryset:
            obj.soft_delete(user=request.user)

    @admin.action(description='بازگردانی انتخاب شده‌ها')
    def restore_selected(self, request, queryset):
        queryset.update(
            is_deleted=False,
            deleted_at=None,
            deleted_by=None
        )