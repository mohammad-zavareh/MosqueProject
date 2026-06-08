from django import forms
from .models import InventoryTransaction, InventoryItem, InventoryCategory, Supplier
from app_finance.models import ExpenseDetail

_INPUT    = {"class": "form-ctrl"}
_SELECT   = {"class": "form-ctrl"}
_TEXTAREA = {"class": "form-ctrl", "rows": "3"}
_NUMBER   = {"class": "form-ctrl", "type": "number", "min": "0", "step": "0.01"}
_DATE     = {"class": "form-ctrl", "type": "date"}


class InventoryTransactionForm(forms.ModelForm):

    class Meta:
        model  = InventoryTransaction
        fields = [
            "item", "transaction_type", "quantity",
            "unit_price", "date", "expense", "notes",
        ]
        widgets = {
            "item":             forms.Select(attrs={**_SELECT, "id": "id_item"}),
            "transaction_type": forms.Select(attrs={**_SELECT, "id": "id_transaction_type"}),
            "quantity":         forms.NumberInput(attrs={
                                    **_NUMBER,
                                    "placeholder": "مقدار",
                                    "id": "id_quantity",
                                }),
            "unit_price":       forms.NumberInput(attrs={
                                    **_NUMBER,
                                    "placeholder": "قیمت واحد",
                                    "id": "id_unit_price",
                                }),
            "date":             forms.DateInput(attrs={**_DATE, "id": "id_date"}),
            "expense":          forms.Select(attrs={**_SELECT, "id": "id_expense"}),
            "notes":            forms.Textarea(attrs={
                                    **_TEXTAREA,
                                    "placeholder": "یادداشت (اختیاری)...",
                                    "id": "id_notes",
                                }),
        }
        labels = {
            "item":             "کالا",
            "transaction_type": "نوع تراکنش",
            "quantity":         "مقدار",
            "unit_price":       "قیمت واحد (تومان)",
            "date":             "تاریخ",
            "expense":          "سند هزینه مرتبط",
            "notes":            "یادداشت",
        }
        error_messages = {
            "item":             {"required": "انتخاب کالا الزامی است."},
            "transaction_type": {"required": "نوع تراکنش الزامی است."},
            "quantity":         {"required": "مقدار الزامی است."},
            "date":             {"required": "تاریخ الزامی است."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["item"].queryset = (
            InventoryItem.objects
            .filter(is_deleted=False)
            .select_related("category")
            .order_by("category__name", "name")
        )
        self.fields["item"].empty_label = "— انتخاب کالا —"

        expense_qs = (
            ExpenseDetail.objects
            .filter(is_deleted=False)
            .select_related("transaction", "category")
            .order_by("-transaction__date")
        )
        self.fields["expense"].queryset    = expense_qs
        self.fields["expense"].empty_label = "— بدون سند هزینه —"
        self.fields["expense"].required    = False

        # نمایش شماره مرجع در dropdown
        self.fields["expense"].label_from_instance = self._expense_label

    @staticmethod
    def _expense_label(obj):
        txn = obj.transaction
        ref = txn.reference_number or f"#{txn.pk}"
        date = txn.date.strftime("%Y/%m/%d") if txn.date else "—"
        amount = f"{txn.amount:,.0f}"
        cat = obj.category.name if obj.category_id else "—"
        return f"{ref}  |  {date}  |  {amount} تومان  |  {cat}"

        # total_price فقط نمایشی است و در save() محاسبه می‌شود





class InventoryItemForm(forms.ModelForm):
    class Meta:
        model  = InventoryItem
        fields = [
            "name", "category", "unit",
            "purchase_price", "current_stock", "supplier",
        ]
        widgets = {
            "name":           forms.TextInput(attrs={
                                  **_INPUT,
                                  "placeholder": "نام کالا",
                              }),
            "category":       forms.Select(attrs=_SELECT),
            "unit":           forms.TextInput(attrs={
                                  **_INPUT,
                                  "placeholder": "مثال: عدد، کیلوگرم، متر",
                              }),
            "purchase_price": forms.NumberInput(attrs={
                                  **_NUMBER,
                                  "placeholder": "قیمت خرید",
                              }),
            "current_stock":  forms.NumberInput(attrs={
                                  **_NUMBER,
                                  "placeholder": "موجودی اولیه",
                              }),
            "supplier":       forms.Select(attrs=_SELECT),
        }
        labels = {
            "name":           "نام کالا",
            "category":       "دسته‌بندی",
            "unit":           "واحد",
            "purchase_price": "قیمت خرید (تومان)",
            "current_stock":  "موجودی اولیه",
            "supplier":       "تأمین‌کننده",
        }
        error_messages = {
            "name":     {"required": "نام کالا الزامی است."},
            "category": {"required": "انتخاب دسته‌بندی الزامی است."},
            "unit":     {"required": "واحد الزامی است."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = (
            InventoryCategory.objects
            .filter(is_deleted=False)
            .order_by("name")
        )
        self.fields["category"].empty_label = "— انتخاب دسته‌بندی —"
        self.fields["supplier"].queryset = (
            Supplier.objects
            .filter(is_deleted=False)
            .order_by("name")
        )
        self.fields["supplier"].empty_label = "— بدون تأمین‌کننده —"
        self.fields["supplier"].required    = False



class SupplierForm(forms.ModelForm):
    class Meta:
        model  = Supplier
        fields = ["name", "phone", "address"]
        widgets = {
            "name":    forms.TextInput(attrs={
                           **_INPUT,
                           "placeholder": "نام تأمین‌کننده",
                       }),
            "phone":   forms.TextInput(attrs={
                           **_INPUT,
                           "placeholder": "مثال: ۰۹۱۲۳۴۵۶۷۸۹",
                       }),
            "address": forms.Textarea(attrs={
                           **_TEXTAREA,
                           "placeholder": "آدرس (اختیاری)...",
                       }),
        }
        labels = {
            "name":    "نام تأمین‌کننده",
            "phone":   "شماره تماس",
            "address": "آدرس",
        }
        error_messages = {
            "name": {"required": "نام تأمین‌کننده الزامی است."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["phone"].required   = False
        self.fields["address"].required = False


class InventoryCategoryForm(forms.ModelForm):
    class Meta:
        model   = InventoryCategory
        fields  = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-ctrl",
                "placeholder": "نام دسته‌بندی انبار",
            })
        }
        labels        = {"name": "نام دسته‌بندی"}
        error_messages = {"name": {"required": "نام دسته‌بندی الزامی است."}}