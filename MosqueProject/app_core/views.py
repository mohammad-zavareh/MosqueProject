from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Q, F
from django.utils import timezone
from django.views.generic import TemplateView
from django.contrib.auth import get_user_model
from .models import AuditLog
from app_finance.models import FinancialTransaction, Fund, Event
from app_inventory.models import InventoryItem, Supplier
from .jalali_utils import parse_jalali_date
import jdatetime
import json
import os
import io
import zipfile
from django.apps import apps
from django.conf import settings
from django.core import serializers
from django.db import transaction as db_transaction
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views import View
from django.http import HttpResponse, JsonResponse, HttpResponseForbidden


User = get_user_model()

ACTION_LABELS_MAP = {
    "CREATE": ("ایجاد", "bdg-green"),
    "UPDATE": ("ویرایش", "bdg-blue"),
    "DELETE": ("حذف", "bdg-red"),
}

MODEL_LABELS_MAP = {
    "financialtransaction": "تراکنش مالی",
    "incomedetail":         "جزئیات درآمد",
    "expensedetail":        "جزئیات هزینه",
    "inventoryitem":        "کالای انبار",
    "inventorytransaction": "تراکنش انبار",
    "supplier":             "تأمین‌کننده",
    "fund":                 "صندوق",
    "event":                "مناسبت",
    "incomecategory":       "دسته درآمد",
    "expensecategory":      "دسته هزینه",
    "inventorycategory":    "دسته انبار",
}


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    MONTH_NAMES = [
        "", "فروردین", "اردیبهشت", "خرداد", "تیر",
        "مرداد", "شهریور", "مهر", "آبان", "آذر",
        "دی", "بهمن", "اسفند",
    ]

    def get(self, request, *args, **kwargs):
        now        = timezone.now()
        this_month = now.replace(day=1).date()

        # ── ماه قبل (برای محاسبه روند) ────────────────────
        if this_month.month == 1:
            prev_month_start = this_month.replace(year=this_month.year - 1, month=12)
        else:
            prev_month_start = this_month.replace(month=this_month.month - 1)
        prev_month_end = this_month

        base_qs = FinancialTransaction.objects.filter(is_deleted=False)

        # ── مالی این ماه ──────────────────────────────────
        month_income = base_qs.filter(
            transaction_type="INCOME", date__gte=this_month
        ).aggregate(s=Sum("amount"))["s"] or 0
        month_expense = base_qs.filter(
            transaction_type="EXPENSE", date__gte=this_month
        ).aggregate(s=Sum("amount"))["s"] or 0
        month_balance = month_income - month_expense
        month_txn_count = base_qs.filter(date__gte=this_month).count()

        # ── مالی ماه قبل ───────────────────────────────────
        prev_income = base_qs.filter(
            transaction_type="INCOME",
            date__gte=prev_month_start, date__lt=prev_month_end,
        ).aggregate(s=Sum("amount"))["s"] or 0
        prev_expense = base_qs.filter(
            transaction_type="EXPENSE",
            date__gte=prev_month_start, date__lt=prev_month_end,
        ).aggregate(s=Sum("amount"))["s"] or 0

        def _trend(cur, prev):
            if not prev:
                return None
            return round((float(cur) - float(prev)) / float(prev) * 100)

        income_trend  = _trend(month_income, prev_income)
        expense_trend = _trend(month_expense, prev_expense)

        # ── جمع کل تاریخچه ─────────────────────────────────
        total_income_all  = base_qs.filter(transaction_type="INCOME").aggregate(s=Sum("amount"))["s"] or 0
        total_expense_all = base_qs.filter(transaction_type="EXPENSE").aggregate(s=Sum("amount"))["s"] or 0
        total_balance_all = total_income_all - total_expense_all

        # ── آخرین ۶ تراکنش ────────────────────────────────
        recent_txns = (
            base_qs
            .select_related(
                "fund",
                "income_detail__category",
                "expense_detail__category",
            )
            .order_by("-date", "-created_at")[:6]
        )

        # ── گردش هر صندوق ──────────────────────────────────
        funds = Fund.objects.filter(is_deleted=False).annotate(
            inc=Sum("transactions__amount",
                    filter=Q(transactions__transaction_type="INCOME", transactions__is_deleted=False)),
            exp=Sum("transactions__amount",
                    filter=Q(transactions__transaction_type="EXPENSE", transactions__is_deleted=False)),
        ).order_by("name")

        fund_rows = []
        for f in funds:
            inc = f.inc or 0
            exp = f.exp or 0
            fund_rows.append({"name": f.name, "balance": inc - exp, "income": inc, "expense": exp})

        max_fund_balance = max([abs(r["balance"]) for r in fund_rows], default=0) or 1
        for row in fund_rows:
            row["pct"] = round(abs(row["balance"]) / max_fund_balance * 100)

        # ── تفکیک دسته‌بندی هزینه/درآمد این ماه (Top 5) ────
        top_expense_cats = (
            base_qs.filter(transaction_type="EXPENSE", date__gte=this_month)
            .values("expense_detail__category__name")
            .annotate(total=Sum("amount"))
            .order_by("-total")[:5]
        )
        exp_cat_max = max([c["total"] for c in top_expense_cats], default=0) or 1
        expense_cat_data = [
            {
                "name": c["expense_detail__category__name"] or "بدون دسته",
                "total": c["total"] or 0,
                "pct": round((c["total"] or 0) / exp_cat_max * 100),
            }
            for c in top_expense_cats
        ]

        top_income_cats = (
            base_qs.filter(transaction_type="INCOME", date__gte=this_month)
            .values("income_detail__category__name")
            .annotate(total=Sum("amount"))
            .order_by("-total")[:5]
        )
        inc_cat_max = max([c["total"] for c in top_income_cats], default=0) or 1
        income_cat_data = [
            {
                "name": c["income_detail__category__name"] or "بدون دسته",
                "total": c["total"] or 0,
                "pct": round((c["total"] or 0) / inc_cat_max * 100),
            }
            for c in top_income_cats
        ]

        # ── موجودی انبار ─────────────────────────────────
        inv_qs = InventoryItem.objects.filter(is_deleted=False)
        inventory_items = (
            inv_qs.select_related("category", "supplier").order_by("current_stock")[:6]
        )
        # ← FIX: قبلاً فقط Sum(current_stock) بود (مقدار، نه ارزش)
        total_inventory_value = inv_qs.aggregate(
            v=Sum(F("current_stock") * F("purchase_price"))
        )["v"] or 0
        low_stock_count   = inv_qs.filter(current_stock__gt=0, current_stock__lt=5).count()
        zero_stock_count  = inv_qs.filter(current_stock__lte=0).count()
        total_items_count = inv_qs.count()

        top_used_items = (
            inv_qs.annotate(used=Sum(
                "transactions__quantity",
                filter=Q(transactions__transaction_type="USAGE",
                         transactions__is_deleted=False,
                         transactions__date__gte=this_month)
            ))
            .filter(used__isnull=False)
            .order_by("-used")[:5]
        )

        # ── نمودار ۶ ماه گذشته (بر اساس تقویم شمسی) ─────────────────────
        today_j = jdatetime.date.fromgregorian(date=now.date())
        chart_data = []
        for i in range(5, -1, -1):
            back = today_j.month - 1 - i
            year_offset, month_index = divmod(back, 12)
            j_year, j_month = today_j.year + year_offset, month_index + 1

            start = jdatetime.date(j_year, j_month, 1).togregorian()
            if j_month == 12:
                end = jdatetime.date(j_year + 1, 1, 1).togregorian()
            else:
                end = jdatetime.date(j_year, j_month + 1, 1).togregorian()

            inc = base_qs.filter(transaction_type="INCOME", date__gte=start, date__lt=end).aggregate(s=Sum("amount"))[
                      "s"] or 0
            exp = base_qs.filter(transaction_type="EXPENSE", date__gte=start, date__lt=end).aggregate(s=Sum("amount"))[
                      "s"] or 0

            chart_data.append({
                "label": self.MONTH_NAMES[j_month],
                "inc": float(inc),
                "exp": float(exp),
            })

        max_val = max((max(d["inc"], d["exp"]) for d in chart_data), default=1) or 1
        for d in chart_data:
            d["inc_pct"] = round(d["inc"] / max_val * 100)
            d["exp_pct"] = round(d["exp"] / max_val * 100)

        # ── آخرین فعالیت‌های حسابرسی ────────────────────────
        recent_activity = list(
            AuditLog.objects.select_related("user").order_by("-timestamp")[:6]
        )
        for log in recent_activity:
            info = ACTION_LABELS_MAP.get(log.action, (log.action, "bdg-muted"))
            log.action_label = info[0]
            log.action_badge = info[1]
            log.model_label  = MODEL_LABELS_MAP.get(log.model_name, log.model_name)

        # ── آمار کلی سیستم ───────────────────────────────
        stats = {
            "funds_count":     Fund.objects.filter(is_deleted=False).count(),
            "suppliers_count": Supplier.objects.filter(is_deleted=False).count(),
            "users_count":     User.objects.filter(is_active=True).count(),
            "events_count":    Event.objects.filter(is_deleted=False).count(),
        }

        ctx = {
            "current_month": self.MONTH_NAMES[now.month],

            "month_income":  month_income,
            "month_expense": month_expense,
            "month_balance": month_balance,
            "income_trend":  income_trend,
            "expense_trend": expense_trend,
            "month_txn_count": month_txn_count,

            "total_income_all":  total_income_all,
            "total_expense_all": total_expense_all,
            "total_balance_all": total_balance_all,

            "recent_txns": recent_txns,
            "fund_rows":   fund_rows,

            "expense_cat_data": expense_cat_data,
            "income_cat_data":  income_cat_data,

            "inventory_items":       inventory_items,
            "total_inventory_value": total_inventory_value,
            "low_stock_count":       low_stock_count,
            "zero_stock_count":      zero_stock_count,
            "total_items_count":     total_items_count,
            "top_used_items":        top_used_items,

            "chart_data": chart_data,

            "recent_activity": recent_activity,
            "stats": stats,
        }
        return self.render_to_response(ctx)



# بخش حسابداری

ACTION_LABELS = {
    "CREATE": ("ایجاد",   "bdg-green"),
    "UPDATE": ("ویرایش",  "bdg-blue"),
    "DELETE": ("حذف",     "bdg-red"),
}

MODEL_LABELS = {
    "financialtransaction": "تراکنش مالی",
    "incomedetail":         "جزئیات درآمد",
    "expensedetail":        "جزئیات هزینه",
    "inventoryitem":        "کالای انبار",
    "inventorytransaction": "تراکنش انبار",
    "supplier":             "تأمین‌کننده",
    "fund":                 "صندوق",
    "event":                "مناسبت",
    "incomecategory":       "دسته درآمد",
    "expensecategory":      "دسته هزینه",
    "inventorycategory":    "دسته انبار",
}


class AuditLogListView(LoginRequiredMixin, TemplateView):
    template_name = "audit_list.html"
    PAGINATE_BY   = 25

    def get(self, request, *args, **kwargs):
        p = request.GET
        qs = AuditLog.objects.select_related("user", "content_type")

        # ── فیلترها ─────────────────────────────────────
        q = p.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(object_repr__icontains=q)
                | Q(user__username__icontains=q)
                | Q(user__first_name__icontains=q)
                | Q(user__last_name__icontains=q)
            )

        action = p.get("action", "")
        if action in ("CREATE", "UPDATE", "DELETE"):
            qs = qs.filter(action=action)

        model = p.get("model", "")
        if model:
            qs = qs.filter(model_name=model)

        user_id = p.get("user", "")
        if user_id.isdigit():
            qs = qs.filter(user_id=user_id)

        # ← فقط همین یک بلاک باید باشه، جای بلاک قدیمی
        date_from = p.get("date_from", "").strip()
        date_to = p.get("date_to", "").strip()
        parsed_from = parse_jalali_date(date_from)
        parsed_to = parse_jalali_date(date_to)
        if parsed_from:
            qs = qs.filter(timestamp__date__gte=parsed_from)
        if parsed_to:
            qs = qs.filter(timestamp__date__lte=parsed_to)

        # ── صفحه‌بندی ────────────────────────────────────
        try:
            page = max(1, int(p.get("page", 1)))
        except (ValueError, TypeError):
            page = 1

        total = qs.count()
        page_count = max(1, (total + self.PAGINATE_BY - 1) // self.PAGINATE_BY)
        page = min(page, page_count)
        start = (page - 1) * self.PAGINATE_BY
        logs = qs[start: start + self.PAGINATE_BY]

        for log in logs:
            info = ACTION_LABELS.get(log.action, (log.action, "bdg-muted"))
            log.action_label = info[0]
            log.action_badge = info[1]
            log.model_label = MODEL_LABELS.get(log.model_name, log.model_name)

        params = p.copy()
        params.pop("page", None)
        qs_no_page = ("&" + params.urlencode()) if params else ""

        summary = {
            "total": total,
            "create": AuditLog.objects.filter(action="CREATE").count(),
            "update": AuditLog.objects.filter(action="UPDATE").count(),
            "delete": AuditLog.objects.filter(action="DELETE").count(),
        }

        ctx = {
            "logs": logs,
            "total": total,
            "page": page,
            "page_count": page_count,
            "has_prev": page > 1,
            "has_next": page < page_count,
            "prev_page": page - 1,
            "next_page": page + 1,
            "start_index": start + 1,
            "end_index": min(start + self.PAGINATE_BY, total),
            "qs_no_page": qs_no_page,
            "summary": summary,
            "users": User.objects.filter(audit_logs__isnull=False).distinct().order_by("username"),
            "models": sorted(MODEL_LABELS.items()),
            "f_q": q,
            "f_action": action,
            "f_model": model,
            "f_user": user_id,
            "f_date_from": date_from,  # ← رشته خام شمسی، برای نمایش توی input
            "f_date_to": date_to,
            "has_filters": any([q, action, model, user_id, date_from, date_to]),
        }
        return self.render_to_response(ctx)


class AuditLogDetailView(LoginRequiredMixin, TemplateView):
    """جزئیات یک لاگ — نمایش تغییرات field به field"""
    template_name = "audit_detail.html"

    def get(self, request, pk, *args, **kwargs):
        from django.shortcuts import get_object_or_404
        log = get_object_or_404(
            AuditLog.objects.select_related("user", "content_type"),
            pk=pk,
        )
        log.action_label = ACTION_LABELS.get(log.action, (log.action, ""))[0]
        log.action_badge = ACTION_LABELS.get(log.action, ("", "bdg-muted"))[1]
        log.model_label  = MODEL_LABELS.get(log.model_name, log.model_name)

        # تبدیل changes به لیست قابل نمایش
        changes_list = []
        for field, vals in log.changes.items():
            if field == "_new":
                # ایجاد — همه فیلدها رو نشون بده
                for k, v in vals.items():
                    changes_list.append({
                        "field":  k,
                        "before": "—",
                        "after":  v,
                        "is_new": True,
                    })
            else:
                changes_list.append({
                    "field":  field,
                    "before": vals.get("before", "—"),
                    "after":  vals.get("after",  "—"),
                    "is_new": False,
                })

        ctx = {
            "log":          log,
            "changes_list": changes_list,
        }
        return self.render_to_response(ctx)




# ══════════════════════════════════════════════════════════════
#  پشتیبان‌گیری کامل (Export / Import)
# ══════════════════════════════════════════════════════════════

# ترتیب مدل‌ها بر اساس وابستگی FK — رعایت این ترتیب هنگام import ضروریست
BACKUP_MODELS_ORDER = [
    "auth.user",
    "app_finance.fund",
    "app_finance.event",
    "app_finance.incomecategory",
    "app_finance.expensecategory",
    "app_finance.financialtransaction",
    "app_finance.incomedetail",
    "app_finance.expensedetail",
    "app_inventory.supplier",
    "app_inventory.inventorycategory",
    "app_inventory.inventoryitem",
    "app_inventory.inventorytransaction",
]

# مدل‌هایی که به خودشون FK دارن (parent) و باید بر اساس عمق مرتب بشن
SELF_REF_MODELS = {
    "app_finance.incomecategory",
    "app_finance.expensecategory",
}


def _ordered_queryset(model_label):
    """
    برای دسته‌بندی‌های خودارجاع، ابتدا ریشه‌ها و بعد فرزندان
    (بر اساس عمق) برگردانده می‌شود تا در import خطای FK رخ ندهد.
    """
    model = apps.get_model(model_label)
    if model_label not in SELF_REF_MODELS:
        return list(model.objects.all().order_by("pk"))

    ordered = []
    added_ids = set()
    remaining = list(model.objects.all().order_by("pk"))

    while remaining:
        progressed = False
        still_remaining = []
        for obj in remaining:
            if obj.parent_id is None or obj.parent_id in added_ids:
                ordered.append(obj)
                added_ids.add(obj.pk)
                progressed = True
            else:
                still_remaining.append(obj)
        remaining = still_remaining
        if not progressed:
            # اگر حلقه‌ای معیوب بود (نباید پیش بیاد)، بقیه رو همونطور اضافه کن
            ordered.extend(remaining)
            break

    return ordered


class BackupView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """صفحه‌ی اصلی پشتیبان‌گیری — شامل export و import"""
    template_name = "backup.html"

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        return HttpResponseForbidden("دسترسی غیرمجاز — این بخش فقط برای سوپر ادمین است.")


class BackupExportView(LoginRequiredMixin, UserPassesTestMixin, View):
    """خروجی کامل به‌صورت ZIP شامل data.json + فایل‌های مدیا"""

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        return HttpResponseForbidden("دسترسی غیرمجاز")

    def get(self, request, *args, **kwargs):
        all_objects = []
        for label in BACKUP_MODELS_ORDER:
            all_objects.extend(_ordered_queryset(label))

        data_json = serializers.serialize("json", all_objects, indent=None)

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("data.json", data_json)
            zf.writestr("meta.json", json.dumps({
                "app": "MosqueProject",
                "version": 1,
                "exported_at": timezone.now().isoformat(),
                "models_order": BACKUP_MODELS_ORDER,
            }, ensure_ascii=False, indent=2))

            media_root = settings.MEDIA_ROOT
            if os.path.isdir(media_root):
                for root, _, files in os.walk(media_root):
                    for fname in files:
                        full_path = os.path.join(root, fname)
                        rel_path = os.path.relpath(full_path, media_root)
                        zf.write(full_path, os.path.join("media", rel_path))

        zip_bytes = buf.getvalue()
        filename = f"mosque-backup-{timezone.now().strftime('%Y%m%d-%H%M%S')}.zip"

        response = HttpResponse(zip_bytes, content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response["Content-Length"] = str(len(zip_bytes))
        return response


class BackupImportView(LoginRequiredMixin, UserPassesTestMixin, View):
    """بازیابی از فایل ZIP خروجی‌گرفته‌شده توسط همین سامانه"""

    def test_func(self):
        return self.request.user.is_superuser

    def handle_no_permission(self):
        return JsonResponse({"ok": False, "error": "دسترسی غیرمجاز"}, status=403)

    def post(self, request, *args, **kwargs):
        uploaded = request.FILES.get("backup_file")
        if not uploaded:
            return JsonResponse({"ok": False, "error": "فایلی انتخاب نشده است."}, status=400)

        try:
            zf = zipfile.ZipFile(uploaded)
        except zipfile.BadZipFile:
            return JsonResponse({"ok": False, "error": "فایل معتبر نیست (ZIP نامعتبر)."}, status=400)

        if "data.json" not in zf.namelist():
            return JsonResponse({"ok": False, "error": "فایل data.json در بسته یافت نشد."}, status=400)

        data_json = zf.read("data.json").decode("utf-8")

        created_count = 0
        updated_count = 0

        try:
            with db_transaction.atomic():
                for deserialized_obj in serializers.deserialize("json", data_json):
                    model_cls = type(deserialized_obj.object)
                    pk = deserialized_obj.object.pk
                    exists = pk is not None and model_cls.objects.filter(pk=pk).exists()
                    deserialized_obj.save()
                    if exists:
                        updated_count += 1
                    else:
                        created_count += 1

                # ── استخراج فایل‌های مدیا ──
                media_root = settings.MEDIA_ROOT
                for name in zf.namelist():
                    if name.startswith("media/") and not name.endswith("/"):
                        rel_path = name[len("media/"):]
                        target_path = os.path.join(media_root, rel_path)
                        os.makedirs(os.path.dirname(target_path), exist_ok=True)
                        with open(target_path, "wb") as out_f:
                            out_f.write(zf.read(name))

        except Exception as e:
            return JsonResponse({
                "ok": False,
                "error": f"عملیات بازگردانی متوقف و لغو شد: {str(e)}",
            }, status=400)

        return JsonResponse({
            "ok": True,
            "created": created_count,
            "updated": updated_count,
            "message": "بازیابی اطلاعات با موفقیت انجام شد.",
        })