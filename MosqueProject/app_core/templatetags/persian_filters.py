from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()


@register.filter
def money(value, suffix=""):
    """
    عدد را با جداکننده سه‌رقمی فرمت می‌کند.
    مثال: 2500000 → 2,500,000
    اگر suffix داده شود: 2,500,000 تومان
    """
    try:
        # تبدیل به Decimal برای دقت
        num = Decimal(str(value))
        # حذف اعشار اگه صفر باشه
        if num == num.to_integral_value():
            formatted = "{:,.0f}".format(num)
        else:
            formatted = "{:,.2f}".format(num)
    except (InvalidOperation, TypeError, ValueError):
        return value

    if suffix:
        return f"{formatted} {suffix}"
    return formatted


@register.filter
def money_toman(value):
    """میانبر: عدد + تومان"""
    return money(value, "تومان")
