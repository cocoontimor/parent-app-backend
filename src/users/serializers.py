from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    display_name = serializers.ReadOnlyField()
    role = serializers.SerializerMethodField()
    cohorts = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "full_name",
            "display_name",
            "role",
            "cohorts",
        ]
        read_only_fields = ["id", "username"]

    def get_role(self, user):
        names = {g.name for g in user.groups.all()}
        if "staff" in names:
            return "staff"
        if "teacher" in names:
            return "teacher"
        if "trainee" in names:
            return "trainee"
        return "normal"

    def get_cohorts(self, user):
        return [{"id": c.id, "name": c.name} for c in user.cohorts.all()]
