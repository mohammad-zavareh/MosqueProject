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
    path(
        "category/income/",
        views.IncomeCategoryListView.as_view(),
        name="category_income_list",
    ),
    path(
        "category/income/create/",
        views.IncomeCategoryCreateView.as_view(),
        name="category_income_create",
    ),
    path(
        "category/income/<int:pk>/edit/",
        views.IncomeCategoryUpdateView.as_view(),
        name="category_income_update",
    ),

    # ── هزینه ────────────────────────────────────────────────
    path(
        "category/expense/",
        views.ExpenseCategoryListView.as_view(),
        name="category_expense_list",
    ),
    path(
        "category/expense/create/",
        views.ExpenseCategoryCreateView.as_view(),
        name="category_expense_create",
    ),
    path(
        "category/expense/<int:pk>/edit/",
        views.ExpenseCategoryUpdateView.as_view(),
        name="category_expense_update",
    ),

    # ── صندوق ────────────────────────────────────────────
    path("fund/",views.FundListView.as_view(), name="fund_list"),
    path("fund/create/",views.FundCreateView.as_view(), name="fund_create"),
    path("fund/<int:pk>/edit/",views.FundUpdateView.as_view(), name="fund_update"),

    # ── مناسبت ───────────────────────────────────────────
    path("event/",views.EventListView.as_view(), name="event_list"),
    path("event/create/",views.EventCreateView.as_view(), name="event_create"),
    path("event/<int:pk>/edit/",views.EventUpdateView.as_view(), name="event_update"),

    path("fund-flow/",
         views.FundFlowView.as_view(),
         name="fund_flow"),
    path("report/",
         views.FinanceReportView.as_view(),
         name="finance_report"),
]

# نمونه لینک‌دهی در تمپلیت:
#   {% url 'finance:transaction_create' %}?tab=income
#   {% url 'finance:transaction_create' %}?tab=expense
#   {% url 'finance:transaction_update' pk=txn.pk %}