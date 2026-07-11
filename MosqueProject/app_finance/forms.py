from django import forms
from .models import (
    FinancialTransaction, IncomeDetail, ExpenseDetail,
    IncomeCategory, ExpenseCategory, Fund, Event,
)
from jalali_date_new.fields import JalaliDateField
from jalali_date_new.widgets import AdminJalaliDateWidget

_INPUT    = {"class": "form-ctrl"}
_SELECT   = {"class": "form-ctrl"}
_TEXTAREA = {"class": "form-ctrl", "rows": "3"}
_NUMBER   = {"class": "form-ctrl", "type": "number", "min": "0", "step": "0.01"}


# ── فیلدهای مشترک هر دو فرم ─────────────────────────────────
class TransactionBaseForm(forms.ModelForm):
    class Meta:
        model  = FinancialTransaction
        fields = ["amount", "date", "fund", "event", "reference_number",
                  "description", "image_receipt"]
        widgets = {
            "amount":           forms.NumberInput(attrs={**_NUMBER, "placeholder": "مبلغ به تومان"}),
            "fund":             forms.Select(attrs=_SELECT),
            "event":            forms.Select(attrs=_SELECT),
            "reference_number": forms.TextInput(attrs={**_INPUT, "placeholder": "شماره مرجع / فاکتور"}),
            "description":      forms.Textarea(attrs={**_TEXTAREA, "placeholder": "توضیحات تکمیلی..."}),
            "image_receipt":    forms.ClearableFileInput(attrs={
                                    "class": "form-ctrl-file",
                                    "accept": "image/*,application/pdf",
                                }),
        }
        labels = {
            "amount": "مبلغ (تومان)", "date": "تاریخ",
            "fund": "صندوق", "event": "رویداد",
            "reference_number": "شماره مرجع", "description": "توضیحات",
            "image_receipt": "تصویر رسید",
        }
        error_messages = {
            "amount": {"required": "مبلغ الزامی است."},
            "date":   {"required": "تاریخ الزامی است."},
            "fund":   {"required": "انتخاب صندوق الزامی است."},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fund"].empty_label  = "— انتخاب صندوق —"
        self.fields["event"].empty_label = "— انتخاب رویداد —"
        self.fields["event"].required    = False
        self.fields["fund"].queryset     = Fund.objects.only("id", "name").order_by("name")
        self.fields["event"].queryset    = Event.objects.only("id", "name").order_by("name")
        self.fields["date"] = JalaliDateField(label="تاریخ",widget=AdminJalaliDateWidget(attrs={"class": "form-ctrl"}))

# ── فیلدهای اختصاصی درآمد ────────────────────────────────────
class IncomeDetailForm(forms.ModelForm):
    # hidden — مقدار توسط JS ویجت کتگوری ست می‌شه
    category = forms.ModelChoiceField(
        queryset=IncomeCategory.objects.all(),
        widget=forms.HiddenInput(attrs={"id": "id_inc_category"}),
        required=True,
        error_messages={"required": "انتخاب دسته‌بندی درآمد الزامی است."},
        label="دسته‌بندی درآمد",
    )

    class Meta:
        model   = IncomeDetail
        fields  = ["category", "payer_name"]
        widgets = {
            "payer_name": forms.TextInput(attrs={
                **_INPUT,
                "placeholder": "نام پرداخت‌کننده (اختیاری)",
                "id": "id_payer_name",
            }),
        }
        labels  = {"payer_name": "نام پرداخت‌کننده"}


# ── فیلدهای اختصاصی هزینه ────────────────────────────────────
class ExpenseDetailForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=ExpenseCategory.objects.all(),
        widget=forms.HiddenInput(attrs={"id": "id_exp_category"}),
        required=True,
        error_messages={"required": "انتخاب دسته‌بندی هزینه الزامی است."},
        label="دسته‌بندی هزینه",
    )

    class Meta:
        model   = ExpenseDetail
        fields  = ["category", "vendor_name"]
        widgets = {
            "vendor_name": forms.TextInput(attrs={
                **_INPUT,
                "placeholder": "نام تأمین‌کننده / فروشنده (اختیاری)",
                "id": "id_vendor_name",
            }),
        }
        labels  = {"vendor_name": "نام تأمین‌کننده"}





_INPUT  = {"class": "form-ctrl"}
_SELECT = {"class": "form-ctrl"}


class IncomeCategoryForm(forms.ModelForm):
    class Meta:
        model  = IncomeCategory
        fields = ["name", "parent"]
        widgets = {
            "name":   forms.TextInput(attrs={**_INPUT,
                          "placeholder": "نام دسته‌بندی درآمد"}),
            "parent": forms.Select(attrs=_SELECT),
        }
        labels = {
            "name":   "نام دسته‌بندی",
            "parent": "دسته‌بندی والد",
        }
        error_messages = {
            "name": {"required": "نام دسته‌بندی الزامی است."},
        }

    def __init__(self, *args, **kwargs):
        # instance موجود را از parent choices حذف می‌کنیم
        # تا دسته نتواند والد خودش باشد
        instance = kwargs.get("instance")
        super().__init__(*args, **kwargs)
        self.fields["parent"].required    = False
        self.fields["parent"].empty_label = "— بدون والد (ریشه) —"
        qs = IncomeCategory.objects.filter(is_deleted=False)
        if instance and instance.pk:
            # خود دسته و تمام فرزندانش را حذف می‌کنیم
            exclude_ids = self._get_subtree_ids(instance)
            qs = qs.exclude(pk__in=exclude_ids)
        self.fields["parent"].queryset = qs.order_by("name")

    @staticmethod
    def _get_subtree_ids(node):
        """pk تمام زیردرخت یک نود را برمی‌گرداند."""
        ids = [node.pk]
        for child in node.children.filter(is_deleted=False):
            ids.extend(IncomeCategoryForm._get_subtree_ids(child))
        return ids


class ExpenseCategoryForm(forms.ModelForm):
    class Meta:
        model  = ExpenseCategory
        fields = ["name", "parent"]
        widgets = {
            "name":   forms.TextInput(attrs={**_INPUT,
                          "placeholder": "نام دسته‌بندی هزینه"}),
            "parent": forms.Select(attrs=_SELECT),
        }
        labels = {
            "name":   "نام دسته‌بندی",
            "parent": "دسته‌بندی والد",
        }
        error_messages = {
            "name": {"required": "نام دسته‌بندی الزامی است."},
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get("instance")
        super().__init__(*args, **kwargs)
        self.fields["parent"].required    = False
        self.fields["parent"].empty_label = "— بدون والد (ریشه) —"
        qs = ExpenseCategory.objects.filter(is_deleted=False)
        if instance and instance.pk:
            exclude_ids = self._get_subtree_ids(instance)
            qs = qs.exclude(pk__in=exclude_ids)
        self.fields["parent"].queryset = qs.order_by("name")

    @staticmethod
    def _get_subtree_ids(node):
        ids = [node.pk]
        for child in node.children.filter(is_deleted=False):
            ids.extend(ExpenseCategoryForm._get_subtree_ids(child))
        return ids



_TEXTAREA = {"class": "form-ctrl", "rows": "3"}


class FundForm(forms.ModelForm):
    class Meta:
        model  = Fund
        fields = ["name", "description"]
        widgets = {
            "name":        forms.TextInput(attrs={
                               **_INPUT,
                               "placeholder": "نام صندوق را وارد کنید",
                           }),
            "description": forms.Textarea(attrs={
                               **_TEXTAREA,
                               "placeholder": "توضیحات (اختیاری)...",
                           }),
        }
        labels = {"name": "نام صندوق", "description": "توضیحات"}
        error_messages = {
            "name": {"required": "نام صندوق الزامی است."}
        }


class EventForm(forms.ModelForm):
    class Meta:
        model  = Event
        fields = ["name", "description"]
        widgets = {
            "name":        forms.TextInput(attrs={
                               **_INPUT,
                               "placeholder": "نام مناسبت را وارد کنید",
                           }),
            "description": forms.Textarea(attrs={
                               **_TEXTAREA,
                               "placeholder": "توضیحات (اختیاری)...",
                           }),
        }
        labels = {"name": "نام مناسبت", "description": "توضیحات"}
        error_messages = {
            "name": {"required": "نام مناسبت الزامی است."}
        }
