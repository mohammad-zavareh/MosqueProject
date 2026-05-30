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
    path("item/",
         views.InventoryItemListView.as_view(),
         name="item_list"),
    path("item/create/",
         views.InventoryItemCreateView.as_view(),
         name="item_create"),
    path("item/<int:pk>/edit/",
         views.InventoryItemUpdateView.as_view(),
         name="item_update"),
    path(
        "supplier/",
        views.SupplierListView.as_view(),
        name="supplier_list",
    ),
    path(
        "supplier/create/",
        views.SupplierCreateView.as_view(),
        name="supplier_create",
    ),
    path(
        "supplier/<int:pk>/edit/",
        views.SupplierUpdateView.as_view(),
        name="supplier_update",
    ),
]
