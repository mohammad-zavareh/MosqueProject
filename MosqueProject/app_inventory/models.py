from django.db import models
from app_core.models import BaseModel
from app_finance.models import ExpenseDetail
from decimal import Decimal


class Supplier(BaseModel):

    name = models.CharField(max_length=255)

    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True
    )

    address = models.TextField(
        blank=True
    )

    class Meta:
        verbose_name = "تامین کننده"
        verbose_name_plural = "تامین کنندگان"

    def __str__(self):
        return self.name


class InventoryCategory(BaseModel):

    name = models.CharField(max_length=100)


    class Meta:
        verbose_name = "دسته انبار"
        verbose_name_plural = "دسته‌بندی انبار"

    def __str__(self):
        return self.name


class InventoryItem(BaseModel):

    name = models.CharField(max_length=255)

    item_code = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        verbose_name="کد کالا",
    )

    category = models.ForeignKey(
        InventoryCategory,
        on_delete=models.PROTECT,
        related_name='items'
    )

    unit = models.CharField(
        max_length=50
    )

    current_stock = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    purchase_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='items'
    )

    class Meta:
        verbose_name = "کالای انبار"
        verbose_name_plural = "کالاهای انبار"

    def recalculate_stock(self):
        """
        موجودی کالا رو از روی تاریخچه‌ی تراکنش‌های ثبت‌شده
        (به ترتیب تاریخ) از نو محاسبه می‌کند.
        خرید = افزایش، مصرف = کاهش، اصلاح = تنظیم مطلق.
        """
        stock = Decimal('0')
        txns = (
            self.transactions
            .filter(is_deleted=False)
            .order_by('date', 'created_at', 'pk')
        )
        for t in txns:
            if t.transaction_type == 'PURCHASE':
                stock += t.quantity
            elif t.transaction_type == 'USAGE':
                stock -= t.quantity
            elif t.transaction_type == 'ADJUSTMENT':
                stock = t.quantity

        InventoryItem.objects.filter(pk=self.pk).update(current_stock=stock)
        self.current_stock = stock

    def __str__(self):
        return self.name


class InventoryTransaction(BaseModel):

    TRANSACTION_TYPES = [
        ('PURCHASE', 'خرید'),
        ('USAGE', 'مصرف'),
        ('ADJUSTMENT', 'اصلاح موجودی'),
    ]

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name='transactions'
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES
    )

    quantity = models.DecimalField(
        max_digits=14,
        decimal_places=2
    )

    unit_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    total_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=0
    )

    date = models.DateField()

    notes = models.TextField(
        blank=True
    )

    # تغییر از OneToOne به ForeignKey
    expense = models.ForeignKey(
        ExpenseDetail,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inventory_transactions'
    )

    class Meta:
        verbose_name = "تراکنش انبار"
        verbose_name_plural = "تراکنش‌های انبار"

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price

        # اگه ویرایشه و کالا عوض شده، باید موجودی کالای قبلی هم بازمحاسبه بشه
        old_item_id = None
        if self.pk:
            old = (
                InventoryTransaction.objects
                .filter(pk=self.pk)
                .values_list('item_id', flat=True)
                .first()
            )
            old_item_id = old

        super().save(*args, **kwargs)

        self.item.recalculate_stock()
        if old_item_id and old_item_id != self.item_id:
            InventoryItem.objects.get(pk=old_item_id).recalculate_stock()

    def delete(self, *args, **kwargs):
        item = self.item
        super().delete(*args, **kwargs)
        item.recalculate_stock()

    def soft_delete(self, user=None):
        super().soft_delete(user=user)
        self.item.recalculate_stock()

    def __str__(self):
        return f"{self.item} - {self.transaction_type}"
