from django.urls import path
from .views import DashboardView,AuditLogListView, AuditLogDetailView


app_name = "core"

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),

    path("audit/", AuditLogListView.as_view(), name="audit_list"),
    path( "audit/<int:pk>/", AuditLogDetailView.as_view(), name="audit_detail",
    ),

]