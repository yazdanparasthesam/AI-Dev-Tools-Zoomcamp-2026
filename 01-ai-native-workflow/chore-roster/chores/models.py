"""Domain models for the Chore Roster app."""

from datetime import timedelta

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

AVATAR_COLORS = [
    "#5b8cff", "#ff8f5b", "#3ecf8e", "#c77dff", "#ffd166", "#ff6b9d",
]


class Member(models.Model):
    """A person living in the household."""

    name = models.CharField(max_length=100)
    email = models.EmailField(blank=True)
    color = models.CharField(max_length=7, default=AVATAR_COLORS[0])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.pk and self.color == AVATAR_COLORS[0]:
            self.color = AVATAR_COLORS[Member.objects.count() % len(AVATAR_COLORS)]
        super().save(*args, **kwargs)

    @property
    def initials(self):
        parts = self.name.split()
        return "".join(p[0].upper() for p in parts[:2]) or "?"

    @property
    def points(self):
        return sum(c.points_awarded for c in self.completions.all())

    @property
    def completion_count(self):
        return self.completions.count()

    @property
    def open_chore_count(self):
        return self.chores.filter(is_active=True).count()


class Chore(models.Model):
    """A recurring task that rotates through household members."""

    DAILY, WEEKLY, BIWEEKLY, MONTHLY = "daily", "weekly", "biweekly", "monthly"
    RECURRENCE_CHOICES = [
        (DAILY, "Daily"),
        (WEEKLY, "Weekly"),
        (BIWEEKLY, "Every 2 weeks"),
        (MONTHLY, "Monthly"),
    ]
    RECURRENCE_DAYS = {DAILY: 1, WEEKLY: 7, BIWEEKLY: 14, MONTHLY: 30}

    ROTATE, KEEP = "rotate", "keep"
    ASSIGNMENT_CHOICES = [(ROTATE, "Rotate to next member"), (KEEP, "Always same member")]

    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    recurrence = models.CharField(max_length=10, choices=RECURRENCE_CHOICES, default=WEEKLY)
    assignment_mode = models.CharField(max_length=10, choices=ASSIGNMENT_CHOICES, default=ROTATE)
    assigned_to = models.ForeignKey(
        Member, null=True, blank=True, on_delete=models.SET_NULL, related_name="chores"
    )
    difficulty = models.PositiveSmallIntegerField(
        default=2, validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="1 = trivial, 5 = a whole afternoon. Drives points awarded.",
    )
    due_date = models.DateField(default=timezone.localdate)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_date", "name"]

    def __str__(self):
        return self.name

    # ---- derived ---------------------------------------------------------
    @property
    def points(self):
        """Points a member earns for completing this chore."""
        return self.difficulty * 10

    @property
    def days_until_due(self):
        return (self.due_date - timezone.localdate()).days

    @property
    def status(self):
        days = self.days_until_due
        if days < 0:
            return "overdue"
        if days == 0:
            return "today"
        if days <= 3:
            return "soon"
        return "upcoming"

    # ---- behaviour -------------------------------------------------------
    def next_member(self):
        """The member who should own this chore after the current one finishes."""
        members = list(Member.objects.filter(is_active=True))
        if not members:
            return None
        if self.assignment_mode == self.KEEP:
            return self.assigned_to or members[0]
        ids = [m.id for m in members]
        if self.assigned_to_id not in ids:
            return members[0]
        return members[(ids.index(self.assigned_to_id) + 1) % len(members)]

    def mark_done(self, note="", by=None):
        """Log a completion, rotate the assignee and roll the due date forward."""
        completion = Completion.objects.create(
            chore=self,
            completed_by=by or self.assigned_to,
            note=note,
            points_awarded=self.points,
            was_late=self.days_until_due < 0,
        )
        today = timezone.localdate()
        step = timedelta(days=self.RECURRENCE_DAYS[self.recurrence])
        # never leave the chore in the past: catch up to at least today
        next_due = self.due_date + step
        while next_due < today:
            next_due += step
        self.due_date = next_due
        self.assigned_to = self.next_member()
        self.save()
        return completion

    def snooze(self, days=1):
        self.due_date += timedelta(days=days)
        self.save(update_fields=["due_date"])
        return self


class Completion(models.Model):
    """An immutable log entry: someone finished a chore."""

    chore = models.ForeignKey(Chore, on_delete=models.CASCADE, related_name="completions")
    completed_by = models.ForeignKey(
        Member, null=True, blank=True, on_delete=models.SET_NULL, related_name="completions"
    )
    completed_at = models.DateTimeField(auto_now_add=True)
    note = models.CharField(max_length=200, blank=True)
    points_awarded = models.PositiveIntegerField(default=0)
    was_late = models.BooleanField(default=False)

    class Meta:
        ordering = ["-completed_at"]

    def __str__(self):
        return f"{self.chore} by {self.completed_by} on {self.completed_at:%Y-%m-%d}"
