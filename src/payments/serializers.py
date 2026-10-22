from rest_framework import serializers

from .models import FeePayment


class FeePaymentSerializer(serializers.ModelSerializer):
    child_name = serializers.CharField(source="child.name", read_only=True)
    marked_by_name = serializers.CharField(
        source="marked_by.display_name", read_only=True, default=None
    )

    class Meta:
        model = FeePayment
        fields = [
            "id",
            "child",
            "child_name",
            "month",
            "amount",
            "status",
            "paid_at",
            "marked_by_name",
            "created",
            "modified",
        ]
        read_only_fields = ["id", "created", "modified"]
