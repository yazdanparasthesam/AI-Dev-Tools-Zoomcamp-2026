from rest_framework import serializers

from .models import Chore, Completion, Member


class MemberSerializer(serializers.ModelSerializer):
    initials = serializers.ReadOnlyField()
    points = serializers.ReadOnlyField()
    completion_count = serializers.ReadOnlyField()
    open_chore_count = serializers.ReadOnlyField()

    class Meta:
        model = Member
        fields = [
            "id", "name", "email", "color", "is_active", "initials",
            "points", "completion_count", "open_chore_count", "created_at",
        ]
        read_only_fields = ["created_at"]


class ChoreSerializer(serializers.ModelSerializer):
    assigned_to_name = serializers.CharField(source="assigned_to.name", read_only=True, default=None)
    assigned_to_color = serializers.CharField(source="assigned_to.color", read_only=True, default=None)
    recurrence_display = serializers.CharField(source="get_recurrence_display", read_only=True)
    status = serializers.ReadOnlyField()
    points = serializers.ReadOnlyField()
    days_until_due = serializers.ReadOnlyField()

    class Meta:
        model = Chore
        fields = [
            "id", "name", "description", "recurrence", "recurrence_display",
            "assignment_mode", "assigned_to", "assigned_to_name", "assigned_to_color",
            "difficulty", "points", "due_date", "days_until_due", "status",
            "is_active", "created_at",
        ]
        read_only_fields = ["created_at"]

    def validate_difficulty(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Difficulty must be between 1 and 5.")
        return value


class CompletionSerializer(serializers.ModelSerializer):
    chore_name = serializers.CharField(source="chore.name", read_only=True)
    member_name = serializers.CharField(source="completed_by.name", read_only=True, default=None)
    member_color = serializers.CharField(source="completed_by.color", read_only=True, default=None)

    class Meta:
        model = Completion
        fields = [
            "id", "chore", "chore_name", "completed_by", "member_name", "member_color",
            "completed_at", "note", "points_awarded", "was_late",
        ]
        read_only_fields = fields


class MarkDoneSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, max_length=200)
    completed_by = serializers.PrimaryKeyRelatedField(
        queryset=Member.objects.all(), required=False, allow_null=True
    )


class SnoozeSerializer(serializers.Serializer):
    days = serializers.IntegerField(required=False, default=1, min_value=1, max_value=30)
