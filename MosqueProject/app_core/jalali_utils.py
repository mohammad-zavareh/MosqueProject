import re
import jdatetime

_FA_TO_EN = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")


def parse_jalali_date(value):
    """رشته تاریخ شمسی (مثل 1403/05/10) رو به datetime.date میلادی تبدیل می‌کند."""
    if not value:
        return None
    value = str(value).translate(_FA_TO_EN).strip()
    m = re.match(r"^(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})$", value)
    if not m:
        return None
    y, mo, d = map(int, m.groups())
    try:
        return jdatetime.date(y, mo, d).togregorian()
    except ValueError:
        return None


def to_jalali_str(date_obj, fmt="%Y/%m/%d"):
    """datetime.date میلادی رو برای مقدار پیش‌فرض input ها به رشته شمسی تبدیل می‌کند."""
    if not date_obj:
        return ""
    return jdatetime.date.fromgregorian(date=date_obj).strftime(fmt)