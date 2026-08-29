from rest_framework import serializers

from .models import FeePayment


class FeePaymentSerializer(serializers.ModelSerializer):
    child_name = serializers.CharField(source="child.name", read_only=True)

    class Meta:
        model = FeePayment
        fields = ["id", "child", "child_name", "month", "amount", "created", "modified"]
        read_only_fields = ["id", "created", "modified"]
