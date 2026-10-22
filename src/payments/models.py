from django.conf import settings
from django.db import models

from utils.models import BaseModel


class FeePayment(BaseModel):
    """A monthly school-fee invoice for a child.

    Generated as ``pending`` for a month, then marked ``paid`` when the receipt
    is taken (or ``waived`` for exempt children). One row per child per month.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        WAIVED = "waived", "Waived"

    child = models.ForeignKey(
        "children.Child",
        on_delete=models.CASCADE,
        related_name="payments",
    )
    month = models.CharField(
        max_length=7,
        help_text="Month the payment covers, formatted as YYYY-MM (e.g. 2026-08).",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="marked_payments",
    )

    class Meta:
        db_table = "fee_payments"
        ordering = ["-month"]
        unique_together = [("child", "month")]

    def __str__(self):
        return f"{self.child} — {self.month}: {self.status}"
