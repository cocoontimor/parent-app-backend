from rest_framework import serializers

from .models import Child, Circle


class ChildSerializer(serializers.ModelSerializer):
    class Meta:
        model = Child
        fields = ["id", "name", "date_of_birth", "created", "modified"]
        read_only_fields = ["id", "created", "modified"]


class CircleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Circle
        fields = ["id", "name", "type", "members", "children", "created", "modified"]
        read_only_fields = ["id", "created", "modified"]
