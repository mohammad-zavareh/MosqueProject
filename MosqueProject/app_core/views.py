from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.views.generic import TemplateView

from app_finance.models import FinancialTransaction
from app_inventory.models import InventoryItem


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "dashboard.html"

    def get(self, request, *args, **kwargs):
        now        = timezone.now()
        this_month = now.replace(day=1).date()

        # ── مالی این ماه ──────────────────────────────────
        month_income = (
            FinancialTransaction.objects
            .filter(transaction_type="INCOME",
                    is_deleted=False,
                    date__gte=this_month)
            .aggregate(s=Sum("amount"))["s"] or 0
        )
        month_expense = (
            FinancialTransaction.objects
            .filter(transaction_type="EXPENSE",
                    is_deleted=False,
                    date__gte=this_month)
            .aggregate(s=Sum("amount"))["s"] or 0
        )
        month_balance = month_income - month_expense

        # ── آخرین ۷ تراکنش ────────────────────────────────
        recent_txns = (
            FinancialTransaction.objects
            .filter(is_deleted=False)
            .select_related(
                "fund",
                "income_detail__category",
                "expense_detail__category",
            )
            .order_by("-date", "-created_at")[:7]
        )

        # ── موجودی انبار ─────────────────────────────────
        inventory_items = (
            InventoryItem.objects
            .filter(is_deleted=False)
            .select_related("category", "supplier")
            .order_by("current_stock")[:8]
        )
        total_inventory_value = (
            InventoryItem.objects
            .filter(is_deleted=False)
            .aggregate(
                v=Sum("current_stock")
            )["v"] or 0
        )
        low_stock_count = (
            InventoryItem.objects
            .filter(is_deleted=False, current_stock__lt=5)
            .count()
        )
        zero_stock_count = (
            InventoryItem.objects
            .filter(is_deleted=False, current_stock__lte=0)
            .count()
        )

        # ── نمودار: ۶ ماه گذشته ───────────────────────────
        chart_data = []
        MONTH_NAMES = [
            "", "فروردین", "اردیبهشت", "خرداد", "تیر",
            "مرداد", "شهریور", "مهر", "آبان", "آذر",
            "دی", "بهمن", "اسفند",
        ]
        for i in range(5, -1, -1):
            # برگشت i ماه از ماه جاری
            month_num  = now.month - i
            year_num   = now.year
            while month_num <= 0:
                month_num += 12
                year_num  -= 1

            if month_num == 12:
                next_month = 1
                next_year  = year_num + 1
            else:
                next_month = month_num + 1
                next_year  = year_num

            import datetime
            start = datetime.date(year_num, month_num, 1)
            try:
                end = datetime.date(next_year, next_month, 1)
            except ValueError:
                continue

            inc = (FinancialTransaction.objects
                   .filter(transaction_type="INCOME",
                           is_deleted=False,
                           date__gte=start, date__lt=end)
                   .aggregate(s=Sum("amount"))["s"] or 0)
            exp = (FinancialTransaction.objects
                   .filter(transaction_type="EXPENSE",
                           is_deleted=False,
                           date__gte=start, date__lt=end)
                   .aggregate(s=Sum("amount"))["s"] or 0)

            chart_data.append({
                "label": MONTH_NAMES[month_num],
                "inc":   float(inc),
                "exp":   float(exp),
            })

        # نرمال‌سازی برای ارتفاع نوارها (حداکثر ۱۰۰٪)
        max_val = max((max(d["inc"], d["exp"]) for d in chart_data), default=1) or 1
        for d in chart_data:
            d["inc_pct"] = round(d["inc"] / max_val * 100)
            d["exp_pct"] = round(d["exp"] / max_val * 100)

        ctx = {
            "month_income":         month_income,
            "month_expense":        month_expense,
            "month_balance":        month_balance,
            "recent_txns":          recent_txns,
            "inventory_items":      inventory_items,
            "total_inventory_value":total_inventory_value,
            "low_stock_count":      low_stock_count,
            "zero_stock_count":     zero_stock_count,
            "chart_data":           chart_data,
            "current_month":        MONTH_NAMES[now.month],
        }
        return self.render_to_response(ctx)
