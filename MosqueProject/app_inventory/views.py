from django.views.generic import ListView
from .models import InventoryItem


class InventoryItemListView(ListView):
    model = InventoryItem
    template_name = 'inventory_item_list.html'