from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction as db_transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import TemplateView, ListView

from .forms import TransactionBaseForm, IncomeDetailForm, ExpenseDetailForm
from .models import (
    FinancialTransaction, IncomeDetail, ExpenseDetail,
    IncomeCategory, ExpenseCategory,
)

class TransactionListView(LoginRequiredMixin, ListView):
    model = FinancialTransaction
    template_name = "transaction_list.html"


# ── کمکی: کتگوری → dict ──────────────────────────────────────
def _cat_json(c):
    return {"id": c.pk, "name": c.name, "has_children": c.children.exists()}

def _ancestors(category):
    path, node = [], category
    while node:
        path.append({"id": node.pk, "name": node.name})
        node = getattr(node, "parent", None)
    path.reverse()
    return path


# ── Ajax کتگوری‌های تو در تو ─────────────────────────────────
class CategoryChildrenView(LoginRequiredMixin, View):
    """
    GET /finance/transaction/ajax/categories/
        ?type=income|expense  &  parent_id=<pk>   (parent_id اختیاری)
    """
    def get(self, request):
        kind      = request.GET.get("type", "income")
        parent_id = request.GET.get("parent_id") or None
        Model     = IncomeCategory if kind == "income" else ExpenseCategory
        qs = (Model.objects.filter(parent_id=parent_id)
              if parent_id else Model.objects.filter(parent__isnull=True))
        return JsonResponse({"categories": [_cat_json(c) for c in qs.order_by("name")]})


# ── context مشترک هر دو ویو ──────────────────────────────────
def _build_ctx(inc_base, inc_detail, exp_base, exp_detail,
               active_tab, instance=None):
    inc_ancestors = exp_ancestors = []
    if instance:
        try:
            inc_ancestors = _ancestors(instance.income_detail.category)
        except IncomeDetail.DoesNotExist:
            pass
        try:
            exp_ancestors = _ancestors(instance.expense_detail.category)
        except ExpenseDetail.DoesNotExist:
            pass
    return {
        "inc_base":       inc_base,
        "inc_detail":     inc_detail,
        "exp_base":       exp_base,
        "exp_detail":     exp_detail,
        "active_tab":     active_tab,   # 'income' | 'expense'
        "instance":       instance,
        "inc_ancestors":  inc_ancestors,
        "exp_ancestors":  exp_ancestors,
    }


# ── ثبت جدید ─────────────────────────────────────────────────
class TransactionCreateView(LoginRequiredMixin, TemplateView):
    template_name = "transaction_form.html"

    def get(self, request, *args, **kwargs):
        # ?tab=expense برای باز شدن مستقیم تب هزینه
        tab = request.GET.get("tab", "income")
        ctx = _build_ctx(
            TransactionBaseForm(prefix="inc"),
            IncomeDetailForm(prefix="inc_d"),
            TransactionBaseForm(prefix="exp"),
            ExpenseDetailForm(prefix="exp_d"),
            active_tab=tab,
        )
        return self.render_to_response(ctx)

    def post(self, request, *args, **kwargs):
        # hidden input _active_tab مشخص می‌کند کدام فرم submit شده
        tab = request.POST.get("_active_tab", "income")

        if tab == "income":
            inc_base   = TransactionBaseForm(request.POST, request.FILES, prefix="inc")
            inc_detail = IncomeDetailForm(request.POST, prefix="inc_d")
            exp_base   = TransactionBaseForm(prefix="exp")
            exp_detail = ExpenseDetailForm(prefix="exp_d")
            active_base, active_detail, txn_type = inc_base, inc_detail, "INCOME"
        else:
            inc_base   = TransactionBaseForm(prefix="inc")
            inc_detail = IncomeDetailForm(prefix="inc_d")
            exp_base   = TransactionBaseForm(request.POST, request.FILES, prefix="exp")
            exp_detail = ExpenseDetailForm(request.POST, prefix="exp_d")
            active_base, active_detail, txn_type = exp_base, exp_detail, "EXPENSE"

        if active_base.is_valid() and active_detail.is_valid():
            with db_transaction.atomic():
                txn = active_base.save(commit=False)
                txn.transaction_type = txn_type
                txn.save()
                det = active_detail.save(commit=False)
                det.transaction = txn
                det.save()
            label = "درآمد" if txn_type == "INCOME" else "هزینه"
            messages.success(request, f"{label} با موفقیت ثبت شد.")
            return redirect("finance:transaction_list")

        ctx = _build_ctx(inc_base, inc_detail, exp_base, exp_detail,
                         active_tab=tab)
        return self.render_to_response(ctx)


# ── ویرایش ───────────────────────────────────────────────────
class TransactionUpdateView(LoginRequiredMixin, TemplateView):
    template_name = "transaction_form.html"

    def _get_txn(self, pk):
        return get_object_or_404(FinancialTransaction, pk=pk)

    def get(self, request, pk, *args, **kwargs):
        txn = self._get_txn(pk)
        tab = "income" if txn.transaction_type == "INCOME" else "expense"

        if txn.transaction_type == "INCOME":
            det = get_object_or_404(IncomeDetail, transaction=txn)
            ctx = _build_ctx(
                TransactionBaseForm(instance=txn, prefix="inc"),
                IncomeDetailForm(instance=det,    prefix="inc_d"),
                TransactionBaseForm(prefix="exp"),
                ExpenseDetailForm(prefix="exp_d"),
                active_tab=tab, instance=txn,
            )
        else:
            det = get_object_or_404(ExpenseDetail, transaction=txn)
            ctx = _build_ctx(
                TransactionBaseForm(prefix="inc"),
                IncomeDetailForm(prefix="inc_d"),
                TransactionBaseForm(instance=txn, prefix="exp"),
                ExpenseDetailForm(instance=det,   prefix="exp_d"),
                active_tab=tab, instance=txn,
            )
        return self.render_to_response(ctx)

    def post(self, request, pk, *args, **kwargs):
        txn = self._get_txn(pk)
        tab = request.POST.get("_active_tab", "income")

        if txn.transaction_type == "INCOME":
            det        = get_object_or_404(IncomeDetail, transaction=txn)
            active_base = TransactionBaseForm(request.POST, request.FILES,
                                              instance=txn, prefix="inc")
            active_det  = IncomeDetailForm(request.POST, instance=det, prefix="inc_d")
            inc_base, inc_detail = active_base, active_det
            exp_base   = TransactionBaseForm(prefix="exp")
            exp_detail = ExpenseDetailForm(prefix="exp_d")
        else:
            det        = get_object_or_404(ExpenseDetail, transaction=txn)
            active_base = TransactionBaseForm(request.POST, request.FILES,
                                              instance=txn, prefix="exp")
            active_det  = ExpenseDetailForm(request.POST, instance=det, prefix="exp_d")
            inc_base   = TransactionBaseForm(prefix="inc")
            inc_detail = IncomeDetailForm(prefix="inc_d")
            exp_base, exp_detail = active_base, active_det

        if active_base.is_valid() and active_det.is_valid():
            with db_transaction.atomic():
                active_base.save()
                active_det.save()
            label = "درآمد" if txn.transaction_type == "INCOME" else "هزینه"
            messages.success(request, f"{label} با موفقیت ویرایش شد.")
            return redirect("finance:transaction_list")

        ctx = _build_ctx(inc_base, inc_detail, exp_base, exp_detail,
                         active_tab=tab, instance=txn)
        return self.render_to_response(ctx)
