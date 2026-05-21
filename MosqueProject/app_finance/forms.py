from django import forms
from .models import (
    FinancialTransaction, IncomeDetail, ExpenseDetail,
    IncomeCategory, ExpenseCategory, Fund, Event,
)

_INPUT    = {"class": "form-ctrl"}
_SELECT   = {"class": "form-ctrl"}
_TEXTAREA = {"class": "form-ctrl", "rows": "3"}
_NUMBER   = {"class": "form-ctrl", "type": "number", "min": "0", "step": "0.01"}
_DATE     = {"class": "form-ctrl", "type": "date"}


# ── فیلدهای مشترک هر دو فرم ─────────────────────────────────
class TransactionBaseForm(forms.ModelForm):
    class Meta:
        model  = FinancialTransaction
        fields = ["amount", "date", "fund", "event", "reference_number",
                  "description", "image_receipt"]
        widgets = {
            "amount":           forms.NumberInput(attrs={**_NUMBER, "placeholder": "مبلغ به تومان"}),
            "date":             forms.DateInput(attrs={**_DATE}),
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
