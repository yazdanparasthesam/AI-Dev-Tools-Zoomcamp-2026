"""JSON REST API for the chore tracker."""

from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import Chore, Completion, Member
from .serializers import (
    ChoreSerializer, CompletionSerializer, MarkDoneSerializer,
    MemberSerializer, SnoozeSerializer,
)


class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("active") == "true":
            qs = qs.filter(is_active=True)
        return qs


class ChoreViewSet(viewsets.ModelViewSet):
    queryset = Chore.objects.select_related("assigned_to")
    serializer_class = ChoreSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if params.get("active") == "true":
            qs = qs.filter(is_active=True)
        if member := params.get("member"):
            qs = qs.filter(assigned_to_id=member)
        if params.get("status") == "overdue":
            qs = qs.filter(due_date__lt=timezone.localdate())
        return qs

    @action(detail=True, methods=["post"])
    def done(self, request, pk=None):
        chore = self.get_object()
        payload = MarkDoneSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        completion = chore.mark_done(
            note=payload.validated_data.get("note", ""),
            by=payload.validated_data.get("completed_by"),
        )
        return Response(
            {
                "completion": CompletionSerializer(completion).data,
                "chore": ChoreSerializer(chore).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def snooze(self, request, pk=None):
        chore = self.get_object()
        payload = SnoozeSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        chore.snooze(payload.validated_data["days"])
        return Response(ChoreSerializer(chore).data)


class CompletionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Completion.objects.select_related("chore", "completed_by")
    serializer_class = CompletionSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        if member := self.request.query_params.get("member"):
            qs = qs.filter(completed_by_id=member)
        if limit := self.request.query_params.get("limit"):
            qs = qs[: int(limit)]
        return qs


@api_view(["GET"])
def dashboard(request):
    """Everything the frontend needs for the home screen, in one round-trip."""
    chores = list(Chore.objects.filter(is_active=True).select_related("assigned_to"))
    buckets = {"overdue": [], "today": [], "soon": [], "upcoming": []}
    for chore in chores:
        buckets[chore.status].append(ChoreSerializer(chore).data)

    members = Member.objects.filter(is_active=True)
    leaderboard = sorted(
        (MemberSerializer(m).data for m in members),
        key=lambda m: (-m["points"], m["name"]),
    )
    week_ago = timezone.now() - timezone.timedelta(days=7)
    recent = Completion.objects.select_related("chore", "completed_by")[:10]

    return Response({
        "buckets": buckets,
        "leaderboard": leaderboard,
        "recent": CompletionSerializer(recent, many=True).data,
        "stats": {
            "total_chores": len(chores),
            "overdue": len(buckets["overdue"]),
            "due_today": len(buckets["today"]),
            "members": members.count(),
            "completed_this_week": Completion.objects.filter(completed_at__gte=week_ago).count(),
            "points_this_week": Completion.objects.filter(completed_at__gte=week_ago).aggregate(
                total=Sum("points_awarded"))["total"] or 0,
        },
    })


@api_view(["GET"])
def stats(request):
    """Aggregates for the stats panel: per-member and per-chore breakdowns."""
    by_member = (
        Completion.objects.values("completed_by__name", "completed_by__color")
        .annotate(count=Count("id"), points=Sum("points_awarded"))
        .order_by("-points")
    )
    by_chore = (
        Completion.objects.values("chore__name")
        .annotate(count=Count("id")).order_by("-count")[:10]
    )
    return Response({
        "by_member": [
            {"name": r["completed_by__name"] or "Unassigned",
             "color": r["completed_by__color"] or "#666",
             "count": r["count"], "points": r["points"] or 0}
            for r in by_member
        ],
        "by_chore": [{"name": r["chore__name"], "count": r["count"]} for r in by_chore],
        "late_rate": round(
            100 * Completion.objects.filter(was_late=True).count()
            / max(Completion.objects.count(), 1), 1),
    })
