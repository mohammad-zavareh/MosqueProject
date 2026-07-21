from django.urls import path
from .views import (
    DashboardView, AuditLogListView, AuditLogDetailView,
    BackupView, BackupExportView, BackupImportView,
)


app_name = "core"

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),

    path("audit/", AuditLogListView.as_view(), name="audit_list"),
    path( "audit/<int:pk>/", AuditLogDetailView.as_view(), name="audit_detail",
    ),

    path("backup/", BackupView.as_view(), name="backup"),
    path("backup/export/", BackupExportView.as_view(), name="backup_export"),
    path("backup/import/", BackupImportView.as_view(), name="backup_import"),
]