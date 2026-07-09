from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction as db_transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.db.models import Count, Sum, Q
from django.views.generic import TemplateView, ListView, DetailView
from app_core.mixin import AuditViewMixin
from .forms import TransactionBaseForm, IncomeDetailForm, ExpenseDetailForm, IncomeCategoryForm, ExpenseCategoryForm, EventForm, FundForm
from .models import (
    FinancialTransaction, IncomeDetail, ExpenseDetail,
    IncomeCategory, ExpenseCategory,Fund, Event
)
import datetime
from django.utils import timezone


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

    def get_paginate_by(self, queryset):
        # وقتی از دکمه «چاپ گزارش کامل» می‌آید، صفحه‌بندی غیرفعال می‌شود
        # تا همهٔ نتایج فیلترشده (نه فقط یک صفحه) نمایش داده شود
        if self.request.GET.get("print") == "1":
            return None
        return self.paginate_by


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

        event_id = p.get("event", "")
        if event_id.isdigit():
            qs = qs.filter(event_id=event_id)

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
        p = self.request.GET

        ctx["funds"] = Fund.objects.only("id", "name").order_by("name")
        ctx["events"] = Event.objects.only("id", "name").order_by("name")

        ctx["f_q"] = p.get("q", "").strip()
        ctx["f_type"] = p.get("type", "").upper()
        ctx["f_fund"] = p.get("fund", "")
        ctx["f_event"] = p.get("event", "")
        ctx["f_date_from"] = p.get("date_from", "").strip()
        ctx["f_date_to"] = p.get("date_to", "").strip()
        ctx["f_amount_min"] = p.get("amount_min", "").strip()
        ctx["f_amount_max"] = p.get("amount_max", "").strip()
        ctx["f_ordering"] = p.get("ordering", "")

        ctx["has_filters"] = any([
            ctx["f_q"], ctx["f_type"], ctx["f_fund"], ctx["f_event"],
            ctx["f_date_from"], ctx["f_date_to"],
            ctx["f_amount_min"], ctx["f_amount_max"],
        ])

        params = p.copy()
        params.pop("page", None)
        params.pop("print", None)
        ctx["qs_no_page"] = ("&" + params.urlencode()) if params else ""

        # ── خلاصهٔ مبلغ روی کل نتایج فیلترشده (نه فقط صفحهٔ فعلی) ──
        full_qs = self.object_list
        sums = full_qs.aggregate(
            total_income=Sum("amount", filter=Q(transaction_type="INCOME")),
            total_expense=Sum("amount", filter=Q(transaction_type="EXPENSE")),
        )
        ctx["sum_income"] = sums["total_income"] or 0
        ctx["sum_expense"] = sums["total_expense"] or 0
        ctx["sum_net"] = ctx["sum_income"] - ctx["sum_expense"]
        ctx["sum_count"] = full_qs.count()

        # ── نام صندوق/مناسبت انتخاب‌شده، برای نمایش در هدر پرینت ──
        ctx["selected_fund_name"] = None
        if ctx["f_fund"]:
            f_obj = Fund.objects.filter(pk=ctx["f_fund"]).first()
            ctx["selected_fund_name"] = f_obj.name if f_obj else None

        ctx["selected_event_name"] = None
        if ctx["f_event"]:
            e_obj = Event.objects.filter(pk=ctx["f_event"]).first()
            ctx["selected_event_name"] = e_obj.name if e_obj else None

        ctx["is_print_mode"] = p.get("print") == "1"

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
class TransactionCreateView(AuditViewMixin, LoginRequiredMixin, TemplateView):
    template_name = "transaction_form.html"

    def get(self, request, *args, **kwargs):
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
            self._log_create(request, txn)
            label = "درآمد" if txn_type == "INCOME" else "هزینه"
            messages.success(request, f"{label} با موفقیت ثبت شد.")
            return redirect("finance:transaction_list")

        ctx = _build_ctx(inc_base, inc_detail, exp_base, exp_detail, active_tab=tab)
        return self.render_to_response(ctx)


class TransactionUpdateView(AuditViewMixin, LoginRequiredMixin, TemplateView):
    template_name = "transaction_form.html"

    def _get_txn(self, pk):
        return get_object_or_404(FinancialTransaction, pk=pk)

    def get(self, request, pk, *args, **kwargs):
        txn = self._get_txn(pk)
        tab = "income" if txn.transaction_type == "INCOME" else "expense"
        # ← snapshot قبل از render
        request.session[f"audit_snap_{pk}"] = self._snapshot(txn)

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
        txn    = self._get_txn(pk)
        tab    = request.POST.get("_active_tab", "income")
        before = request.session.pop(f"audit_snap_{pk}", {})

        if txn.transaction_type == "INCOME":
            det         = get_object_or_404(IncomeDetail, transaction=txn)
            active_base = TransactionBaseForm(request.POST, request.FILES,
                                              instance=txn, prefix="inc")
            active_det  = IncomeDetailForm(request.POST, instance=det, prefix="inc_d")
            inc_base, inc_detail = active_base, active_det
            exp_base   = TransactionBaseForm(prefix="exp")
            exp_detail = ExpenseDetailForm(prefix="exp_d")
        else:
            det         = get_object_or_404(ExpenseDetail, transaction=txn)
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
            self._log_update(request, txn, before)
            label = "درآمد" if txn.transaction_type == "INCOME" else "هزینه"
            messages.success(request, f"{label} با موفقیت ویرایش شد.")
            return redirect("finance:transaction_list")

        ctx = _build_ctx(inc_base, inc_detail, exp_base, exp_detail,
                         active_tab=tab, instance=txn)
        return self.render_to_response(ctx)





# ── کمکی: ساخت درخت ─────────────────────────────────────────
def _build_tree(queryset):
    """
    یک queryset flat را به لیست درختی تبدیل می‌کند.
    هر node: {"obj": instance, "children": [...], "depth": int}
    """
    nodes   = {obj.pk: {"obj": obj, "children": [], "depth": 0}
               for obj in queryset}
    roots   = []
    for pk, node in nodes.items():
        parent_id = node["obj"].parent_id
        if parent_id and parent_id in nodes:
            nodes[parent_id]["children"].append(node)
        else:
            roots.append(node)

    def _set_depth(node, depth):
        node["depth"] = depth
        for child in node["children"]:
            _set_depth(child, depth + 1)

    for root in roots:
        _set_depth(root, 0)

    return roots


def _flatten_tree(tree):
    """درخت را به لیست مسطح عمق‌اول تبدیل می‌کند."""
    result = []
    def _walk(nodes):
        for node in nodes:
            result.append(node)
            _walk(node["children"])
    _walk(tree)
    return result


# ══════════════════════════════════════════════════════════════
#  Mixin مشترک
# ══════════════════════════════════════════════════════════════

class _CategoryMixin:
    """
    kind = 'income' | 'expense'
    """
    kind: str = "income"

    def _model(self):
        return IncomeCategory if self.kind == "income" else ExpenseCategory

    def _form_class(self):
        return IncomeCategoryForm if self.kind == "income" else ExpenseCategoryForm

    def _urls(self):
        return {
            "list":   f"finance:category_{self.kind}_list",
            "create": f"finance:category_{self.kind}_create",
            "update": f"finance:category_{self.kind}_update",
        }

    def _labels(self):
        if self.kind == "income":
            return {"title": "دسته‌بندی درآمد", "badge": "مالی / درآمد"}
        return {"title": "دسته‌بندی هزینه", "badge": "مالی / هزینه"}


# ══════════════════════════════════════════════════════════════
#  لیست درختی
# ══════════════════════════════════════════════════════════════

class CategoryListView(LoginRequiredMixin, _CategoryMixin, TemplateView):
    template_name = "category_list.html"

    def get(self, request, *args, **kwargs):
        qs   = (self._model().objects
                .filter(is_deleted=False)
                .select_related("parent")
                .order_by("parent__name", "name"))
        tree = _build_tree(qs)
        flat = _flatten_tree(tree)
        ctx  = {
            "flat":    flat,
            "kind":    self.kind,
            "labels":  self._labels(),
            "urls":    self._urls(),
            "total":   qs.count(),
            "roots":   sum(1 for n in flat if n["depth"] == 0),
        }
        return self.render_to_response(ctx)


class IncomeCategoryListView(CategoryListView):
    kind = "income"

class ExpenseCategoryListView(CategoryListView):
    kind = "expense"


# ══════════════════════════════════════════════════════════════
#  ایجاد
# ══════════════════════════════════════════════════════════════

class CategoryCreateView(LoginRequiredMixin, _CategoryMixin, TemplateView):
    template_name = "category_form.html"

    def _ctx(self, form):
        return {
            "form":     form,
            "kind":     self.kind,
            "labels":   self._labels(),
            "urls":     self._urls(),
            "instance": None,
        }

    def get(self, request, *args, **kwargs):
        # اگه parent_id در query string بود، فرم رو pre-fill می‌کنیم
        initial = {}
        pid = request.GET.get("parent")
        if pid:
            initial["parent"] = pid
        return self.render_to_response(
            self._ctx(self._form_class()(initial=initial))
        )

    def post(self, request, *args, **kwargs):
        form = self._form_class()(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.updated_by = request.user
            obj.save()
            messages.success(request, f"دسته‌بندی «{obj.name}» با موفقیت ایجاد شد.")
            return redirect(self._urls()["list"])
        return self.render_to_response(self._ctx(form))


class IncomeCategoryCreateView(CategoryCreateView):
    kind = "income"

class ExpenseCategoryCreateView(CategoryCreateView):
    kind = "expense"


# ══════════════════════════════════════════════════════════════
#  ویرایش
# ══════════════════════════════════════════════════════════════

class CategoryUpdateView(LoginRequiredMixin, _CategoryMixin, TemplateView):
    template_name = "category_form.html"

    def _get_obj(self, pk):
        return get_object_or_404(
            self._model(), pk=pk, is_deleted=False
        )

    def _ctx(self, form, obj):
        return {
            "form":     form,
            "kind":     self.kind,
            "labels":   self._labels(),
            "urls":     self._urls(),
            "instance": obj,
        }

    def get(self, request, pk, *args, **kwargs):
        obj = self._get_obj(pk)
        return self.render_to_response(
            self._ctx(self._form_class()(instance=obj), obj)
        )

    def post(self, request, pk, *args, **kwargs):
        obj  = self._get_obj(pk)
        form = self._form_class()(request.POST, instance=obj)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.updated_by = request.user
            updated.save()
            messages.success(
                request, f"دسته‌بندی «{updated.name}» با موفقیت ویرایش شد."
            )
            return redirect(self._urls()["list"])
        return self.render_to_response(self._ctx(form, obj))


class IncomeCategoryUpdateView(CategoryUpdateView):
    kind = "income"

class ExpenseCategoryUpdateView(CategoryUpdateView):
    kind = "expense"




class _ItemMixin:
    """mixin مشترک برای Fund و Event"""
    kind: str = "fund"   # "fund" | "event"

    def _model(self):
        return Fund if self.kind == "fund" else Event

    def _form_class(self):
        return FundForm if self.kind == "fund" else EventForm

    def _labels(self):
        if self.kind == "fund":
            return {
                "title":      "صندوق‌ها",
                "title_sing": "صندوق",
                "badge":      "مالی / صندوق",
                "new":        "صندوق جدید",
                "icon":       "fund",
            }
        return {
            "title":      "مناسبت‌ها",
            "title_sing": "مناسبت",
            "badge":      "مالی / مناسبت",
            "new":        "مناسبت جدید",
            "icon":       "event",
        }

    def _urls(self):
        return {
            "list":   f"finance:{self.kind}_list",
            "create": f"finance:{self.kind}_create",
            "update": f"finance:{self.kind}_update",
        }


# ── لیست ─────────────────────────────────────────────────────
class ItemListView(LoginRequiredMixin, _ItemMixin, TemplateView):
    template_name = "item_list.html"

    def get(self, request, *args, **kwargs):
        q    = request.GET.get("q", "").strip()
        qs   = self._model().objects.filter(is_deleted=False)

        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(description__icontains=q)
            )

        # آمار تراکنش برای هر آیتم
        if self.kind == "fund":
            qs = qs.annotate(
                txn_count   = Count("transactions",
                                    filter=Q(transactions__is_deleted=False)),
                total_income= Sum("transactions__amount",
                                  filter=Q(transactions__transaction_type="INCOME",
                                           transactions__is_deleted=False)),
                total_expense=Sum("transactions__amount",
                                  filter=Q(transactions__transaction_type="EXPENSE",
                                           transactions__is_deleted=False)),
            )
        else:
            qs = qs.annotate(
                txn_count=Count("financialtransaction",
                                filter=Q(financialtransaction__is_deleted=False)),
            )

        qs = qs.order_by("name")

        ctx = {
            "items":   qs,
            "kind":    self.kind,
            "labels":  self._labels(),
            "urls":    self._urls(),
            "q":       q,
            "total":   qs.count(),
        }
        return self.render_to_response(ctx)


class FundListView(ItemListView):
    kind = "fund"

class EventListView(ItemListView):
    kind = "event"


# ── ایجاد ─────────────────────────────────────────────────────
class ItemCreateView(LoginRequiredMixin, _ItemMixin, TemplateView):
    template_name = "item_form.html"

    def _ctx(self, form):
        return {
            "form":     form,
            "kind":     self.kind,
            "labels":   self._labels(),
            "urls":     self._urls(),
            "instance": None,
        }

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self._ctx(self._form_class()()))

    def post(self, request, *args, **kwargs):
        form = self._form_class()(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.updated_by = request.user
            obj.save()
            messages.success(
                request,
                f"{self._labels()['title_sing']} «{obj.name}» با موفقیت ایجاد شد.",
            )
            return redirect(self._urls()["list"])
        return self.render_to_response(self._ctx(form))


class FundCreateView(ItemCreateView):
    kind = "fund"

class EventCreateView(ItemCreateView):
    kind = "event"


# ── ویرایش ────────────────────────────────────────────────────
class ItemUpdateView(LoginRequiredMixin, _ItemMixin, TemplateView):
    template_name = "item_form.html"

    def _get_obj(self, pk):
        return get_object_or_404(self._model(), pk=pk, is_deleted=False)

    def _ctx(self, form, obj):
        return {
            "form":     form,
            "kind":     self.kind,
            "labels":   self._labels(),
            "urls":     self._urls(),
            "instance": obj,
        }

    def get(self, request, pk, *args, **kwargs):
        obj = self._get_obj(pk)
        return self.render_to_response(
            self._ctx(self._form_class()(instance=obj), obj)
        )

    def post(self, request, pk, *args, **kwargs):
        obj  = self._get_obj(pk)
        form = self._form_class()(request.POST, instance=obj)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.updated_by = request.user
            updated.save()
            messages.success(
                request,
                f"{self._labels()['title_sing']} «{updated.name}» با موفقیت ویرایش شد.",
            )
            return redirect(self._urls()["list"])
        return self.render_to_response(self._ctx(form, obj))


class FundUpdateView(ItemUpdateView):
    kind = "fund"

class EventUpdateView(ItemUpdateView):
    kind = "event"



class FundFlowView(LoginRequiredMixin, TemplateView):
    template_name = "fund_flow.html"

    def get(self, request, *args, **kwargs):
        p = request.GET
        today = timezone.now().date()

        # پیش‌فرض: اول ماه جاری تا امروز
        date_from = p.get("date_from", "") or today.replace(day=1).isoformat()
        date_to   = p.get("date_to",   "") or today.isoformat()
        fund_id   = p.get("fund", "")

        try:
            d_from = datetime.date.fromisoformat(date_from)
            d_to   = datetime.date.fromisoformat(date_to)
        except ValueError:
            d_from = today.replace(day=1)
            d_to   = today

        funds = Fund.objects.filter(is_deleted=False).order_by("name")
        selected_fund = None
        if fund_id.isdigit():
            selected_fund = funds.filter(pk=fund_id).first()

        # ── تراکنش‌های بازه ──────────────────────────────
        txn_qs = (
            FinancialTransaction.objects
            .filter(is_deleted=False, date__gte=d_from, date__lte=d_to)
            .select_related("fund",
                            "income_detail__category",
                            "expense_detail__category")
            .order_by("date", "created_at")
        )
        if selected_fund:
            txn_qs = txn_qs.filter(fund=selected_fund)

        # ── موجودی اولیه (قبل از بازه) ───────────────────
        before_qs = FinancialTransaction.objects.filter(
            is_deleted=False, date__lt=d_from
        )
        if selected_fund:
            before_qs = before_qs.filter(fund=selected_fund)

        opening_income  = before_qs.filter(transaction_type="INCOME" ).aggregate(s=Sum("amount"))["s"] or 0
        opening_expense = before_qs.filter(transaction_type="EXPENSE").aggregate(s=Sum("amount"))["s"] or 0
        opening_balance = opening_income - opening_expense

        # ── ساخت سطرهای گردش با موجودی تجمعی ────────────
        rows    = []
        balance = opening_balance
        for txn in txn_qs:
            if txn.transaction_type == "INCOME":
                balance += txn.amount
                cat = txn.income_detail.category.name if hasattr(txn, "income_detail") else "—"
            else:
                balance -= txn.amount
                cat = txn.expense_detail.category.name if hasattr(txn, "expense_detail") else "—"
            rows.append({
                "txn":     txn,
                "cat":     cat,
                "balance": balance,
            })

        # ── جمع‌ها ───────────────────────────────────────
        period_income  = txn_qs.filter(transaction_type="INCOME" ).aggregate(s=Sum("amount"))["s"] or 0
        period_expense = txn_qs.filter(transaction_type="EXPENSE").aggregate(s=Sum("amount"))["s"] or 0
        closing_balance = opening_balance + period_income - period_expense

        ctx = {
            "rows":            rows,
            "funds":           funds,
            "selected_fund":   selected_fund,
            "date_from":       date_from,
            "date_to":         date_to,
            "opening_balance": opening_balance,
            "period_income":   period_income,
            "period_expense":  period_expense,
            "closing_balance": closing_balance,
            "has_filters":     bool(fund_id or p.get("date_from") or p.get("date_to")),
        }
        return self.render_to_response(ctx)



class FinanceReportView(LoginRequiredMixin, TemplateView):
    template_name = "finance_report.html"

    def get(self, request, *args, **kwargs):
        p     = request.GET
        today = timezone.now().date()

        date_from = p.get("date_from", "") or today.replace(day=1).isoformat()
        date_to   = p.get("date_to",   "") or today.isoformat()
        txn_type  = p.get("type", "INCOME").upper()
        if txn_type not in ("INCOME", "EXPENSE"):
            txn_type = "INCOME"

        try:
            d_from = datetime.date.fromisoformat(date_from)
            d_to   = datetime.date.fromisoformat(date_to)
        except ValueError:
            d_from = today.replace(day=1)
            d_to   = today

        # ── جمع کل بازه ──────────────────────────────────
        base_qs = FinancialTransaction.objects.filter(
            is_deleted=False,
            transaction_type=txn_type,
            date__gte=d_from,
            date__lte=d_to,
        )
        total_amount = base_qs.aggregate(s=Sum("amount"))["s"] or 0
        txn_count    = base_qs.count()

        # ── تفکیک بر اساس دسته‌بندی ──────────────────────
        if txn_type == "INCOME":
            by_category = (
                base_qs
                .values("income_detail__category__name")
                .annotate(total=Sum("amount"), count=Count("id"))
                .order_by("-total")
            )
            cat_data = [
                {
                    "name":  r["income_detail__category__name"] or "بدون دسته",
                    "total": r["total"] or 0,
                    "count": r["count"],
                    "pct":   round((r["total"] or 0) / total_amount * 100) if total_amount else 0,
                }
                for r in by_category
            ]
        else:
            by_category = (
                base_qs
                .values("expense_detail__category__name")
                .annotate(total=Sum("amount"), count=Count("id"))
                .order_by("-total")
            )
            cat_data = [
                {
                    "name":  r["expense_detail__category__name"] or "بدون دسته",
                    "total": r["total"] or 0,
                    "count": r["count"],
                    "pct":   round((r["total"] or 0) / total_amount * 100) if total_amount else 0,
                }
                for r in by_category
            ]

        # ── تفکیک ماهانه در بازه ─────────────────────────
        MONTH_FA = ["", "فروردین","اردیبهشت","خرداد","تیر","مرداد","شهریور",
                    "مهر","آبان","آذر","دی","بهمن","اسفند"]
        monthly = []
        cur = d_from.replace(day=1)
        while cur <= d_to:
            if cur.month == 12:
                nxt = cur.replace(year=cur.year + 1, month=1)
            else:
                nxt = cur.replace(month=cur.month + 1)

            m_total = base_qs.filter(
                date__gte=cur,
                date__lt=nxt,
            ).aggregate(s=Sum("amount"))["s"] or 0

            monthly.append({
                "label": MONTH_FA[cur.month],
                "total": float(m_total),
                "pct":   round(float(m_total) / float(total_amount) * 100) if total_amount else 0,
            })
            cur = nxt

        # ── آخرین تراکنش‌ها ───────────────────────────────
        recent = (
            base_qs
            .select_related("fund",
                            "income_detail__category",
                            "expense_detail__category")
            .order_by("-date", "-created_at")[:10]
        )

        ctx = {
            "txn_type":    txn_type,
            "is_income":   txn_type == "INCOME",
            "date_from":   date_from,
            "date_to":     date_to,
            "total_amount":total_amount,
            "txn_count":   txn_count,
            "cat_data":    cat_data,
            "monthly":     monthly,
            "recent":      recent,
            "has_filters": True,
        }
        return self.render_to_response(ctx)
