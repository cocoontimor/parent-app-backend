from rest_framework import serializers

from .models import Update, UrgentAlert


class UpdateSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.display_name", read_only=True)
    child_name = serializers.CharField(source="child.name", read_only=True)

    class Meta:
        model = Update
        fields = [
            "id", "child", "child_name", "text", "photo",
            "created_by", "created_by_name", "created", "modified",
        ]
        read_only_fields = ["id", "created_by", "created", "modified"]


class UrgentAlertSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.display_name", read_only=True)

    class Meta:
        model = UrgentAlert
        fields = [
            "id", "title", "body", "created_by", "created_by_name",
            "created", "modified",
        ]
        read_only_fields = ["id", "created_by", "created", "modified"]
