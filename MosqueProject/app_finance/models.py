from django.db import models
from app_core.models import BaseModel


class Fund(BaseModel):
    name = models.CharField(max_length=100)

    description = models.TextField(
        blank=True
    )

    class Meta:
        verbose_name = "صندوق"
        verbose_name_plural = "صندوق‌ها"

    def __str__(self):
        return self.name


class Event(BaseModel):
    name = models.CharField(max_length=255,verbose_name='نام مناسبت')
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = 'مناسبت'
        verbose_name_plural = 'مناسبت‌ها'

    def __str__(self):
        return self.name


# ---------------------------------------------------------
# Hierarchical Categories
# ---------------------------------------------------------

class IncomeCategory(BaseModel):
    name = models.CharField(max_length=100)

    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='children'
    )

    class Meta:
        verbose_name = "دسته درآمد"
        verbose_name_plural = "دسته‌بندی درآمدها"

    def __str__(self):
        return self.name


class ExpenseCategory(BaseModel):
    name = models.CharField(max_length=100)

    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='children'
    )

    class Meta:
        verbose_name = "دسته هزینه"
        verbose_name_plural = "دسته‌بندی هزینه‌ها"

    def __str__(self):
        return self.name


# ---------------------------------------------------------
# Financial Transaction Base
# ---------------------------------------------------------

class FinancialTransaction(BaseModel):

    TRANSACTION_TYPES = [
        ('INCOME', 'درآمد'),
        ('EXPENSE', 'هزینه'),
    ]

    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES
    )

    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2
    )

    date = models.DateField()

    description = models.TextField(
        blank=True
    )

    fund = models.ForeignKey(
        Fund,
        on_delete=models.PROTECT,
        related_name='transactions'
    )

    image_receipt = models.ImageField(upload_to='images/receipts')

    event = models.ForeignKey(Event,on_delete=models.PROTECT)

    reference_number = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = "تراکنش مالی"
        verbose_name_plural = "تراکنش‌های مالی"

    def __str__(self):
        return f"{self.transaction_type} - {self.amount}"


# ---------------------------------------------------------
# Income Detail
# ---------------------------------------------------------

class IncomeDetail(BaseModel):

    transaction = models.OneToOneField(
        FinancialTransaction,
        on_delete=models.CASCADE,
        related_name='income_detail'
    )

    category = models.ForeignKey(
        IncomeCategory,
        on_delete=models.PROTECT,
        related_name='incomes'
    )

    payer_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = "جزئیات درآمد"
        verbose_name_plural = "جزئیات درآمد"

    def __str__(self):
        return f"Income #{self.id}"


# ---------------------------------------------------------
# Expense Detail
# ---------------------------------------------------------

class ExpenseDetail(BaseModel):

    transaction = models.OneToOneField(
        FinancialTransaction,
        on_delete=models.CASCADE,
        related_name='expense_detail'
    )

    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.PROTECT,
        related_name='expenses'
    )

    vendor_name = models.CharField(
        max_length=255,
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = "جزئیات هزینه"
        verbose_name_plural = "جزئیات هزینه‌ها"

    def __str__(self):
        return f"Expense #{self.id}"
