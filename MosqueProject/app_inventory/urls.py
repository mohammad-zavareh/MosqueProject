from django.urls import path
from . import views

app_name = "inventory"

urlpatterns = [
    path('inventory-item-list/', views.InventoryItemListView.as_view(), name='inventory-item-list'),
]