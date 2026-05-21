from django.db import models
from app_core.models import BaseModel
from app_finance.models import ExpenseDetail


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
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item} - {self.transaction_type}"
