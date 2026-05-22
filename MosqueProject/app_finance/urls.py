from django.urls import path
from . import views

app_name = "finance"

urlpatterns = [
    path(
        "transaction/",
        views.TransactionListView.as_view(),name="transaction_list"),

    path(
        "transaction/<int:pk>/",
        views.TransactionDetailView.as_view(),
        name="transaction_detail",
    ),

    # یک URL برای ثبت — ?tab=income (پیش‌فرض) یا ?tab=expense
    path(
        "transaction/create/",
        views.TransactionCreateView.as_view(),
        name="transaction_create",
    ),
    # ویرایش — نوع از instance خوانده می‌شود، tab خودکار باز می‌شود
    path(
        "transaction/<int:pk>/edit/",
        views.TransactionUpdateView.as_view(),
        name="transaction_update",
    ),
    # Ajax کتگوری‌های تو در تو
    # ?type=income|expense  &  parent_id=<pk>
    path(
        "transaction/ajax/categories/",
        views.CategoryChildrenView.as_view(),
        name="ajax_categories",
    ),
]

# نمونه لینک‌دهی در تمپلیت:
#   {% url 'finance:transaction_create' %}?tab=income
#   {% url 'finance:transaction_create' %}?tab=expense
#   {% url 'finance:transaction_update' pk=txn.pk %}