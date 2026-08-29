from django.db import models

from utils.models import BaseModel


class FeePayment(BaseModel):
    """A manually-logged school fee payment for a child, for a given month."""

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

    class Meta:
        db_table = "fee_payments"
        ordering = ["-month"]

    def __str__(self):
        return f"{self.child} — {self.month}: {self.amount}"
