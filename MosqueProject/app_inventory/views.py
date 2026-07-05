from django.contrib import messages
from django.http import JsonResponse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum, Count
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView, View
from app_core.mixin import AuditViewMixin
from .forms import InventoryTransactionForm, InventoryItemForm, SupplierForm, InventoryCategoryForm
from .models import InventoryTransaction, InventoryItem, InventoryCategory, Supplier


# ══════════════════════════════════════════════════════════════
#  لیست تراکنش‌های انبار
# ══════════════════════════════════════════════════════════════

class InventoryTransactionListView(LoginRequiredMixin, TemplateView):
    template_name = "inv_transaction_list.html"
    PAGINATE_BY = 20

    def get(self, request, *args, **kwargs):
        qs = (
            InventoryTransaction.objects
            .filter(is_deleted=False)
            .select_related(
                "item__category", "item__supplier",
                "expense__transaction",
            )
            .order_by("-date", "-created_at")
        )

        p = request.GET

        # ── فیلترها ─────────────────────────────────────────
        q = p.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(item__name__icontains=q)
                | Q(item__category__name__icontains=q)
                | Q(notes__icontains=q)
            )

        txn_type = p.get("type", "")
        if txn_type in ("PURCHASE", "USAGE", "ADJUSTMENT"):
            qs = qs.filter(transaction_type=txn_type)

        cat_id = p.get("category", "")
        if cat_id.isdigit():
            qs = qs.filter(item__category_id=cat_id)

        filtered_item_name = None
        item_id = p.get("item", "")
        if item_id.isdigit():
            qs = qs.filter(item_id=item_id)
            filtered_item_name = InventoryItem.objects.filter(pk=item_id, is_deleted=False).values_list("name",
                                                                                                        flat=True).first()

        date_from = p.get("date_from", "").strip()
        date_to = p.get("date_to", "").strip()
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        # ── صفحه‌بندی ساده (بدون Paginator جنگو) ────────────
        try:
            page = max(1, int(p.get("page", 1)))
        except (ValueError, TypeError):
            page = 1

        total = qs.count()
        page_count = max(1, (total + self.PAGINATE_BY - 1) // self.PAGINATE_BY)
        page = min(page, page_count)
        start = (page - 1) * self.PAGINATE_BY
        items = qs[start: start + self.PAGINATE_BY]

        # querystring بدون page
        params = p.copy()
        params.pop("page", None)
        qs_no_page = ("&" + params.urlencode()) if params else ""

        # خلاصه آماری
        summary = qs.aggregate(
            total_purchase=Sum("total_price",
                               filter=Q(transaction_type="PURCHASE")),
            total_usage=Sum("total_price",
                            filter=Q(transaction_type="USAGE")),
        )

        ctx = {
            "items": items,
            "total": total,
            "page": page,
            "page_count": page_count,
            "has_prev": page > 1,
            "has_next": page < page_count,
            "prev_page": page - 1,
            "next_page": page + 1,
            "qs_no_page": qs_no_page,
            "start_index": start + 1,
            "end_index": min(start + self.PAGINATE_BY, total),
            "summary": summary,
            "categories": InventoryCategory.objects.filter(is_deleted=False).order_by("name"),
            # فیلترهای فعال
            "f_q": q,
            "f_type": txn_type,
            "f_category": cat_id,
            "f_item": item_id,
            "f_item_name": filtered_item_name,
            "f_date_from": date_from,
            "f_date_to": date_to,
            "has_filters": any([q, txn_type, cat_id, date_from, date_to]),
        }
        return self.render_to_response(ctx)


# ══════════════════════════════════════════════════════════════
#  ایجاد تراکنش انبار
# ══════════════════════════════════════════════════════════════

class InventoryTransactionCreateView(AuditViewMixin, LoginRequiredMixin, TemplateView):
    template_name = "inv_transaction_form.html"

    def _ctx(self, form, instance=None):
        return {
            "form": form,
            "instance": instance,
            "items_json": self._items_json(),
        }

    @staticmethod
    def _items_json():
        import json
        data = {}
        for item in InventoryItem.objects.filter(is_deleted=False).values(
                "id", "unit", "purchase_price", "current_stock"
        ):
            data[str(item["id"])] = {
                "unit": item["unit"],
                "purchase_price": str(item["purchase_price"]),
                "current_stock": str(item["current_stock"]),
            }
        return json.dumps(data, ensure_ascii=False)

    def get(self, request, *args, **kwargs):
        form = InventoryTransactionForm()
        # اگه ?item=pk در URL بود، پیش‌فرض کالا رو ست کن
        item_pk = request.GET.get("item")
        if item_pk:
            form.initial["item"] = item_pk
        return self.render_to_response(self._ctx(form))

    def post(self, request, *args, **kwargs):
        form = InventoryTransactionForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.updated_by = request.user
            obj.save()
            self._log_create(request, obj)
            messages.success(request, f"تراکنش انبار برای «{obj.item.name}» با موفقیت ثبت شد.")
            return redirect("inventory:transaction_list")
        return self.render_to_response(self._ctx(form))


class InventoryTransactionUpdateView(AuditViewMixin, LoginRequiredMixin, TemplateView):
    template_name = "inv_transaction_form.html"

    def _get_obj(self, pk):
        return get_object_or_404(InventoryTransaction, pk=pk, is_deleted=False)

    def _ctx(self, form, instance):
        return {
            "form": form,
            "instance": instance,
            "items_json": InventoryTransactionCreateView._items_json(),
        }

    def get(self, request, pk, *args, **kwargs):
        obj = self._get_obj(pk)
        request.session[f"audit_snap_{pk}"] = self._snapshot(obj)
        return self.render_to_response(self._ctx(InventoryTransactionForm(instance=obj), obj))

    def post(self, request, pk, *args, **kwargs):
        obj = self._get_obj(pk)
        before = request.session.pop(f"audit_snap_{pk}", {})
        form = InventoryTransactionForm(request.POST, instance=obj)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.updated_by = request.user
            updated.save()
            self._log_update(request, obj, before)
            messages.success(request, f"تراکنش «{updated.item.name}» با موفقیت ویرایش شد.")
            return redirect("inventory:transaction_list")
        return self.render_to_response(self._ctx(form, obj))


class InventoryItemListView(LoginRequiredMixin, TemplateView):
    template_name = "inventory_item_list.html"

    def get(self, request, *args, **kwargs):
        qs = (
            InventoryItem.objects
            .filter(is_deleted=False)
            .select_related("category", "supplier")
            .order_by("category__name", "name")
        )

        p = request.GET
        q = p.get("q", "").strip()
        cat_id = p.get("category", "")

        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(category__name__icontains=q)
                | Q(supplier__name__icontains=q)
            )
        if cat_id.isdigit():
            qs = qs.filter(category_id=cat_id)

        ctx = {
            "items": qs,
            "total": qs.count(),
            "categories": InventoryCategory.objects.filter(is_deleted=False).order_by("name"),
            "f_q": q,
            "f_category": cat_id,
            "has_filters": any([q, cat_id]),
        }
        return self.render_to_response(ctx)


class InventoryItemCreateView(AuditViewMixin, LoginRequiredMixin, TemplateView):
    template_name = "inventory_item_form.html"

    def _ctx(self, form, instance=None):
        return {"form": form, "instance": instance}

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self._ctx(InventoryItemForm()))

    def post(self, request, *args, **kwargs):
        form = InventoryItemForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.updated_by = request.user
            obj.save()
            self._log_create(request, obj)
            messages.success(request, f"کالای «{obj.name}» با موفقیت ایجاد شد.")
            return redirect("inventory:item_list")
        return self.render_to_response(self._ctx(form))


class InventoryItemUpdateView(AuditViewMixin, LoginRequiredMixin, TemplateView):
    template_name = "inventory_item_form.html"

    def _get_obj(self, pk):
        return get_object_or_404(InventoryItem, pk=pk, is_deleted=False)

    def _ctx(self, form, instance):
        return {"form": form, "instance": instance}

    def get(self, request, pk, *args, **kwargs):
        obj = self._get_obj(pk)
        # ← FIX: snapshot قبل از return (در نسخه قبل بعد از return بود!)
        request.session[f"audit_snap_{pk}"] = self._snapshot(obj)
        return self.render_to_response(self._ctx(InventoryItemForm(instance=obj), obj))

    def post(self, request, pk, *args, **kwargs):
        obj = self._get_obj(pk)
        before = request.session.pop(f"audit_snap_{pk}", {})
        form = InventoryItemForm(request.POST, instance=obj)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.updated_by = request.user
            updated.save()
            self._log_update(request, obj, before)
            messages.success(request, f"کالای «{updated.name}» با موفقیت ویرایش شد.")
            return redirect("inventory:item_list")
        return self.render_to_response(self._ctx(form, obj))


class SupplierListView(LoginRequiredMixin, TemplateView):
    template_name = "supplier_list.html"

    def get(self, request, *args, **kwargs):
        q = request.GET.get("q", "").strip()
        qs = Supplier.objects.filter(is_deleted=False)

        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(phone__icontains=q)
                | Q(address__icontains=q)
            )

        qs = qs.annotate(
            item_count=Count("items", filter=Q(items__is_deleted=False))
        ).order_by("name")

        ctx = {
            "suppliers": qs,
            "total": qs.count(),
            "q": q,
            "has_filters": bool(q),
        }
        return self.render_to_response(ctx)


class SupplierCreateView(AuditViewMixin, LoginRequiredMixin, TemplateView):
    template_name = "supplier_form.html"

    def _ctx(self, form, instance=None):
        return {"form": form, "instance": instance}

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self._ctx(SupplierForm()))

    def post(self, request, *args, **kwargs):
        form = SupplierForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.updated_by = request.user
            obj.save()
            self._log_create(request, obj)
            messages.success(request, f"تأمین‌کننده «{obj.name}» با موفقیت ایجاد شد.")
            return redirect("inventory:supplier_list")
        return self.render_to_response(self._ctx(form))


class SupplierUpdateView(AuditViewMixin, LoginRequiredMixin, TemplateView):
    template_name = "supplier_form.html"

    def _get_obj(self, pk):
        return get_object_or_404(Supplier, pk=pk, is_deleted=False)

    def _ctx(self, form, instance):
        return {"form": form, "instance": instance}

    def get(self, request, pk, *args, **kwargs):
        obj = self._get_obj(pk)
        # ← snapshot قبل از return
        request.session[f"audit_snap_{pk}"] = self._snapshot(obj)
        return self.render_to_response(self._ctx(SupplierForm(instance=obj), obj))

    def post(self, request, pk, *args, **kwargs):
        obj = self._get_obj(pk)
        before = request.session.pop(f"audit_snap_{pk}", {})
        form = SupplierForm(request.POST, instance=obj)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.updated_by = request.user
            updated.save()
            self._log_update(request, obj, before)
            messages.success(request, f"تأمین‌کننده «{updated.name}» با موفقیت ویرایش شد.")
            return redirect("inventory:supplier_list")
        return self.render_to_response(self._ctx(form, obj))


# ── لیست ────────────────────────────────────────────────
class InventoryCategoryListView(LoginRequiredMixin, TemplateView):
    template_name = "inv_category_list.html"

    def get(self, request, *args, **kwargs):
        qs = (
            InventoryCategory.objects
            .filter(is_deleted=False)
            .annotate(item_count=Count("items", filter=Q(items__is_deleted=False)))
            .order_by("name")
        )
        ctx = {
            "categories": qs,
            "total": qs.count(),
        }
        return self.render_to_response(ctx)


# ── ایجاد ────────────────────────────────────────────────
class InventoryCategoryCreateView(LoginRequiredMixin, TemplateView):
    template_name = "inv_category_form.html"

    def _ctx(self, form, instance=None):
        return {"form": form, "instance": instance}

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self._ctx(InventoryCategoryForm()))

    def post(self, request, *args, **kwargs):
        form = InventoryCategoryForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.updated_by = request.user
            obj.save()
            messages.success(request, f"دسته‌بندی «{obj.name}» با موفقیت ایجاد شد.")
            return redirect("inventory:category_list")
        return self.render_to_response(self._ctx(form))


# ── ویرایش ────────────────────────────────────────────────
class InventoryCategoryUpdateView(LoginRequiredMixin, TemplateView):
    template_name = "inv_category_form.html"

    def _get_obj(self, pk):
        return get_object_or_404(InventoryCategory, pk=pk, is_deleted=False)

    def _ctx(self, form, instance):
        return {"form": form, "instance": instance}

    def get(self, request, pk, *args, **kwargs):
        obj = self._get_obj(pk)
        return self.render_to_response(
            self._ctx(InventoryCategoryForm(instance=obj), obj)
        )

    def post(self, request, pk, *args, **kwargs):
        obj = self._get_obj(pk)
        form = InventoryCategoryForm(request.POST, instance=obj)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.updated_by = request.user
            updated.save()
            messages.success(request, f"دسته‌بندی «{updated.name}» با موفقیت ویرایش شد.")
            return redirect("inventory:category_list")
        return self.render_to_response(self._ctx(form, obj))


class InventoryReportView(LoginRequiredMixin, TemplateView):
    template_name = "inventory_report.html"

    def get(self, request, *args, **kwargs):
        p = request.GET

        # ── فیلتر دسته‌بندی ──────────────────────────────
        cat_id = p.get("category", "")

        items_qs = (
            InventoryItem.objects
            .filter(is_deleted=False)
            .select_related("category", "supplier")
            .annotate(
                total_purchased=Sum(
                    "transactions__quantity",
                    filter=Q(transactions__transaction_type="PURCHASE",
                             transactions__is_deleted=False)
                ),
                total_used=Sum(
                    "transactions__quantity",
                    filter=Q(transactions__transaction_type="USAGE",
                             transactions__is_deleted=False)
                ),
                total_value=Sum(
                    "transactions__total_price",
                    filter=Q(transactions__transaction_type="PURCHASE",
                             transactions__is_deleted=False)
                ),
            )
            .order_by("category__name", "name")
        )
        if cat_id.isdigit():
            items_qs = items_qs.filter(category_id=cat_id)

        # ── آمار کلی ─────────────────────────────────────
        all_items = InventoryItem.objects.filter(is_deleted=False)
        summary = {
            "total_items": all_items.count(),
            "zero_stock": all_items.filter(current_stock__lte=0).count(),
            "low_stock": all_items.filter(current_stock__gt=0, current_stock__lt=5).count(),
            "total_value": all_items.aggregate(
                v=Sum("current_stock")
            )["v"] or 0,
        }

        # ── پرمصرف‌ترین ──────────────────────────────────
        top_used = (
            InventoryItem.objects
            .filter(is_deleted=False)
            .annotate(used=Sum(
                "transactions__quantity",
                filter=Q(transactions__transaction_type="USAGE",
                         transactions__is_deleted=False)
            ))
            .filter(used__isnull=False)
            .order_by("-used")[:5]
        )

        ctx = {
            "items": items_qs,
            "summary": summary,
            "top_used": top_used,
            "categories": InventoryCategory.objects.filter(is_deleted=False).order_by("name"),
            "f_category": cat_id,
            "has_filters": bool(cat_id),
        }
        return self.render_to_response(ctx)


class AjaxItemSearchView(LoginRequiredMixin, View):
    """
    GET /inventory/ajax/items/?q=ITM-001
    جستجو بر اساس item_code یا نام کالا
    """

    def get(self, request):
        q = request.GET.get("q", "").strip()
        qs = (
            InventoryItem.objects
            .filter(is_deleted=False)
            .select_related("category")
        )
        if q:
            qs = qs.filter(
                Q(item_code__icontains=q) | Q(name__icontains=q)
            )
        qs = qs.order_by("item_code")[:20]

        results = [
            {
                "id": item.pk,
                "item_code": item.item_code,
                "name": item.name,
                "unit": item.unit,
                "purchase_price": str(item.purchase_price),
                "current_stock": str(item.current_stock),
                "category": item.category.name,
            }
            for item in qs
        ]
        return JsonResponse({"results": results})


class AjaxExpenseSearchView(LoginRequiredMixin, View):
    """
    GET /inventory/ajax/expenses/?q=REF-001
    جستجو بر اساس reference_number
    """

    def get(self, request):
        from app_finance.models import ExpenseDetail
        q = request.GET.get("q", "").strip()
        qs = (
            ExpenseDetail.objects
            .filter(is_deleted=False)
            .select_related("transaction", "category")
            .order_by("-transaction__date")
        )
        if q:
            qs = qs.filter(
                Q(transaction__reference_number__icontains=q)
                | Q(category__name__icontains=q)
            )
        qs = qs[:20]

        results = []
        for exp in qs:
            txn = exp.transaction
            results.append({
                "id": exp.pk,
                "ref": txn.reference_number or f"#{txn.pk}",
                "date": txn.date.strftime("%Y/%m/%d") if txn.date else "—",
                "amount": f"{txn.amount:,.0f}",
                "category": exp.category.name if exp.category_id else "—",
            })
        return JsonResponse({"results": results})
