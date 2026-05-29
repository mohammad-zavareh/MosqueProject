from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    path(
        "transaction/",
        views.InventoryTransactionListView.as_view(),
        name="transaction_list",
    ),
    path(
        "transaction/create/",
        views.InventoryTransactionCreateView.as_view(),
        name="transaction_create",
    ),
    path(
        "transaction/<int:pk>/edit/",
        views.InventoryTransactionUpdateView.as_view(),
        name="transaction_update",
    ),
]
