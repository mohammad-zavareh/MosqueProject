from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction as db_transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.db.models import Q
from django.views.generic import TemplateView, ListView, DetailView

from .forms import TransactionBaseForm, IncomeDetailForm, ExpenseDetailForm
from .models import (
    FinancialTransaction, IncomeDetail, ExpenseDetail,
    IncomeCategory, ExpenseCategory,Fund
)

class TransactionListView(LoginRequiredMixin, ListView):
    model               = FinancialTransaction
    template_name       = "transaction_list.html"
    context_object_name = "transactions"
    paginate_by         = 15

    SEARCH_FIELDS = [
        "reference_number",
        "description",
        "income_detail__payer_name",
        "expense_detail__vendor_name",
        "income_detail__category__name",
        "expense_detail__category__name",
        "fund__name",
        "event__name",
    ]

    def get_queryset(self):
        qs = (
            FinancialTransaction.objects
            .select_related(
                "fund", "event",
                "income_detail__category",
                "expense_detail__category",
            )
            .order_by("-date", "-created_at")
        )

        p = self.request.GET

        q = p.get("q", "").strip()
        if q:
            cond = Q()
            for f in self.SEARCH_FIELDS:
                cond |= Q(**{f"{f}__icontains": q})
            qs = qs.filter(cond)

        txn_type = p.get("type", "").upper()
        if txn_type in ("INCOME", "EXPENSE"):
            qs = qs.filter(transaction_type=txn_type)

        fund_id = p.get("fund", "")
        if fund_id.isdigit():
            qs = qs.filter(fund_id=fund_id)

        date_from = p.get("date_from", "").strip()
        date_to   = p.get("date_to",   "").strip()
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        amount_min = p.get("amount_min", "").strip()
        amount_max = p.get("amount_max", "").strip()
        if amount_min:
            qs = qs.filter(amount__gte=amount_min)
        if amount_max:
            qs = qs.filter(amount__lte=amount_max)

        ordering = p.get("ordering", "")
        if ordering in ("date", "-date", "amount", "-amount"):
            qs = qs.order_by(ordering)

        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        p   = self.request.GET

        ctx["funds"] = Fund.objects.only("id", "name").order_by("name")

        # فیلترهای فعال — برای نمایش badge و پر کردن فرم
        ctx["f_q"]          = p.get("q",          "").strip()
        ctx["f_type"]       = p.get("type",        "").upper()
        ctx["f_fund"]       = p.get("fund",        "")
        ctx["f_date_from"]  = p.get("date_from",   "").strip()
        ctx["f_date_to"]    = p.get("date_to",     "").strip()
        ctx["f_amount_min"] = p.get("amount_min",  "").strip()
        ctx["f_amount_max"] = p.get("amount_max",  "").strip()
        ctx["f_ordering"]   = p.get("ordering",    "")

        ctx["has_filters"] = any([
            ctx["f_q"], ctx["f_type"], ctx["f_fund"],
            ctx["f_date_from"], ctx["f_date_to"],
            ctx["f_amount_min"], ctx["f_amount_max"],
        ])

        # querystring بدون page — برای لینک‌های pagination
        params = p.copy()
        params.pop("page", None)
        ctx["qs_no_page"] = ("&" + params.urlencode()) if params else ""

        return ctx




class TransactionDetailView(LoginRequiredMixin, DetailView):
    model               = FinancialTransaction
    template_name       = "transaction_detail.html"
    context_object_name = "txn"

    def get_queryset(self):
        return (
            FinancialTransaction.objects
            .select_related(
                "fund", "event",
                "income_detail__category",
                "expense_detail__category",
            )
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        txn = self.object

        ctx["is_income"] = txn.transaction_type == "INCOME"

        if ctx["is_income"]:
            try:
                ctx["detail"]    = txn.income_detail
                ctx["cat_name"]  = txn.income_detail.category.name
                ctx["person"]    = txn.income_detail.payer_name or "—"
                ctx["person_lbl"]= "پرداخت‌کننده"
            except Exception:
                ctx["detail"] = ctx["cat_name"] = ctx["person"] = None
        else:
            try:
                ctx["detail"]    = txn.expense_detail
                ctx["cat_name"]  = txn.expense_detail.category.name
                ctx["person"]    = txn.expense_detail.vendor_name or "—"
                ctx["person_lbl"]= "تأمین‌کننده"
            except Exception:
                ctx["detail"] = ctx["cat_name"] = ctx["person"] = None

        return ctx





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
