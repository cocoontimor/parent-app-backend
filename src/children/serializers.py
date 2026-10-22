from rest_framework import serializers

from .models import Child, Circle


class ChildSerializer(serializers.ModelSerializer):
    class Meta:
        model = Child
        fields = ["id", "name", "date_of_birth", "created", "modified"]
        read_only_fields = ["id", "created", "modified"]


class CircleSerializer(serializers.ModelSerializer):
    member_details = serializers.SerializerMethodField()
    child_details = serializers.SerializerMethodField()

    class Meta:
        model = Circle
        fields = [
            "id",
            "name",
            "type",
            "members",
            "children",
            "member_details",
            "child_details",
            "created",
            "modified",
        ]
        read_only_fields = ["id", "created", "modified"]

    def get_member_details(self, obj):
        return [{"id": m.id, "name": m.display_name} for m in obj.members.all()]

    def get_child_details(self, obj):
        return [{"id": c.id, "name": c.name} for c in obj.children.all()]
