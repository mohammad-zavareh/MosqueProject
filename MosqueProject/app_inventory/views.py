from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum, Count
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView

from .forms import InventoryTransactionForm, InventoryItemForm, SupplierForm
from .models import InventoryTransaction, InventoryItem, InventoryCategory, Supplier


# ══════════════════════════════════════════════════════════════
#  لیست تراکنش‌های انبار
# ══════════════════════════════════════════════════════════════

class InventoryTransactionListView(LoginRequiredMixin, TemplateView):
    template_name = "inv_transaction_list.html"
    PAGINATE_BY   = 20

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

        date_from = p.get("date_from", "").strip()
        date_to   = p.get("date_to",   "").strip()
        if date_from:
            qs = qs.filter(date__gte=date_from)
        if date_to:
            qs = qs.filter(date__lte=date_to)

        # ── صفحه‌بندی ساده (بدون Paginator جنگو) ────────────
        try:
            page = max(1, int(p.get("page", 1)))
        except (ValueError, TypeError):
            page = 1

        total      = qs.count()
        page_count = max(1, (total + self.PAGINATE_BY - 1) // self.PAGINATE_BY)
        page       = min(page, page_count)
        start      = (page - 1) * self.PAGINATE_BY
        items      = qs[start : start + self.PAGINATE_BY]

        # querystring بدون page
        params = p.copy()
        params.pop("page", None)
        qs_no_page = ("&" + params.urlencode()) if params else ""

        # خلاصه آماری
        summary = qs.aggregate(
            total_purchase=Sum("total_price",
                               filter=Q(transaction_type="PURCHASE")),
            total_usage   =Sum("total_price",
                               filter=Q(transaction_type="USAGE")),
        )

        ctx = {
            "items":        items,
            "total":        total,
            "page":         page,
            "page_count":   page_count,
            "has_prev":     page > 1,
            "has_next":     page < page_count,
            "prev_page":    page - 1,
            "next_page":    page + 1,
            "qs_no_page":   qs_no_page,
            "start_index":  start + 1,
            "end_index":    min(start + self.PAGINATE_BY, total),
            "summary":      summary,
            "categories":   InventoryCategory.objects.filter(is_deleted=False).order_by("name"),
            # فیلترهای فعال
            "f_q":          q,
            "f_type":       txn_type,
            "f_category":   cat_id,
            "f_date_from":  date_from,
            "f_date_to":    date_to,
            "has_filters":  any([q, txn_type, cat_id, date_from, date_to]),
        }
        return self.render_to_response(ctx)


# ══════════════════════════════════════════════════════════════
#  ایجاد تراکنش انبار
# ══════════════════════════════════════════════════════════════

class InventoryTransactionCreateView(LoginRequiredMixin, TemplateView):
    template_name = "inv_transaction_form.html"

    def _ctx(self, form, instance=None):
        return {
            "form":     form,
            "instance": instance,
            "items_json": self._items_json(),
        }

    @staticmethod
    def _items_json():
        """اطلاعات کالاها برای autofill قیمت واحد در JS"""
        import json
        data = {}
        for item in InventoryItem.objects.filter(is_deleted=False).values(
            "id", "unit", "purchase_price", "current_stock"
        ):
            data[str(item["id"])] = {
                "unit":           item["unit"],
                "purchase_price": str(item["purchase_price"]),
                "current_stock":  str(item["current_stock"]),
            }
        return json.dumps(data, ensure_ascii=False)

    def get(self, request, *args, **kwargs):
        return self.render_to_response(self._ctx(InventoryTransactionForm()))

    def post(self, request, *args, **kwargs):
        form = InventoryTransactionForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.created_by = request.user
            obj.updated_by = request.user
            obj.save()
            messages.success(
                request,
                f"تراکنش انبار برای «{obj.item.name}» با موفقیت ثبت شد.",
            )
            return redirect("inventory:transaction_list")
        return self.render_to_response(
            self._ctx(form)
        )


# ══════════════════════════════════════════════════════════════
#  ویرایش تراکنش انبار
# ══════════════════════════════════════════════════════════════

class InventoryTransactionUpdateView(LoginRequiredMixin, TemplateView):
    template_name = "inv_transaction_form.html"

    def _get_obj(self, pk):
        return get_object_or_404(InventoryTransaction, pk=pk, is_deleted=False)

    def _ctx(self, form, instance):
        return {
            "form":       form,
            "instance":   instance,
            "items_json": InventoryTransactionCreateView._items_json(),
        }

    def get(self, request, pk, *args, **kwargs):
        obj = self._get_obj(pk)
        return self.render_to_response(
            self._ctx(InventoryTransactionForm(instance=obj), obj)
        )

    def post(self, request, pk, *args, **kwargs):
        obj  = self._get_obj(pk)
        form = InventoryTransactionForm(request.POST, instance=obj)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.updated_by = request.user
            updated.save()
            messages.success(
                request,
                f"تراکنش «{updated.item.name}» با موفقیت ویرایش شد.",
            )
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
        q       = p.get("q", "").strip()
        cat_id  = p.get("category", "")

        if q:
            qs = qs.filter(
                Q(name__icontains=q)
                | Q(category__name__icontains=q)
                | Q(supplier__name__icontains=q)
            )
        if cat_id.isdigit():
            qs = qs.filter(category_id=cat_id)

        ctx = {
            "items":      qs,
            "total":      qs.count(),
            "categories": InventoryCategory.objects.filter(is_deleted=False).order_by("name"),
            "f_q":        q,
            "f_category": cat_id,
            "has_filters": any([q, cat_id]),
        }
        return self.render_to_response(ctx)


class InventoryItemCreateView(LoginRequiredMixin, TemplateView):
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
            messages.success(request, f"کالای «{obj.name}» با موفقیت ایجاد شد.")
            return redirect("inventory:item_list")
        return self.render_to_response(self._ctx(form))


class InventoryItemUpdateView(LoginRequiredMixin, TemplateView):
    template_name = "inventory_item_form.html"

    def _get_obj(self, pk):
        return get_object_or_404(InventoryItem, pk=pk, is_deleted=False)

    def _ctx(self, form, instance):
        return {"form": form, "instance": instance}

    def get(self, request, pk, *args, **kwargs):
        obj = self._get_obj(pk)
        return self.render_to_response(self._ctx(InventoryItemForm(instance=obj), obj))

    def post(self, request, pk, *args, **kwargs):
        obj  = self._get_obj(pk)
        form = InventoryItemForm(request.POST, instance=obj)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.updated_by = request.user
            updated.save()
            messages.success(request, f"کالای «{updated.name}» با موفقیت ویرایش شد.")
            return redirect("inventory:item_list")
        return self.render_to_response(self._ctx(form, obj))





class SupplierListView(LoginRequiredMixin, TemplateView):
    template_name = "supplier_list.html"

    def get(self, request, *args, **kwargs):
        q  = request.GET.get("q", "").strip()
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
            "suppliers":   qs,
            "total":       qs.count(),
            "q":           q,
            "has_filters": bool(q),
        }
        return self.render_to_response(ctx)


class SupplierCreateView(LoginRequiredMixin, TemplateView):
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
            messages.success(
                request,
                f"تأمین‌کننده «{obj.name}» با موفقیت ایجاد شد.",
            )
            return redirect("inventory:supplier_list")
        return self.render_to_response(self._ctx(form))


class SupplierUpdateView(LoginRequiredMixin, TemplateView):
    template_name = "supplier_form.html"

    def _get_obj(self, pk):
        return get_object_or_404(Supplier, pk=pk, is_deleted=False)

    def _ctx(self, form, instance):
        return {"form": form, "instance": instance}

    def get(self, request, pk, *args, **kwargs):
        obj = self._get_obj(pk)
        return self.render_to_response(
            self._ctx(SupplierForm(instance=obj), obj)
        )

    def post(self, request, pk, *args, **kwargs):
        obj  = self._get_obj(pk)
        form = SupplierForm(request.POST, instance=obj)
        if form.is_valid():
            updated = form.save(commit=False)
            updated.updated_by = request.user
            updated.save()
            messages.success(
                request,
                f"تأمین‌کننده «{updated.name}» با موفقیت ویرایش شد.",
            )
            return redirect("inventory:supplier_list")
        return self.render_to_response(self._ctx(form, obj))
