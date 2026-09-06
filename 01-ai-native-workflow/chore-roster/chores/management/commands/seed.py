"""Populate the database with a realistic demo household."""

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from chores.models import Chore, Completion, Member

MEMBERS = [("Ana", "ana@home.local"), ("Ben", "ben@home.local"),
           ("Chi", "chi@home.local"), ("Dev", "")]

CHORES = [
    ("Take out trash", "Bins go out Tuesday night.", "daily", 1, -1),
    ("Wash the dishes", "Empty the drying rack too.", "daily", 2, 0),
    ("Wipe kitchen counters", "", "daily", 1, 0),
    ("Vacuum living room", "Move the couch.", "weekly", 3, 2),
    ("Clean the bathroom", "Sink, toilet, shower.", "weekly", 4, 3),
    ("Mop the floors", "", "weekly", 3, 5),
    ("Water the plants", "Balcony ones need more.", "weekly", 1, 1),
    ("Change bed linen", "", "biweekly", 2, 8),
    ("Deep clean the fridge", "Toss expired stuff.", "monthly", 5, 12),
    ("Clean the windows", "Inside and out.", "monthly", 4, -3),
]


class Command(BaseCommand):
    help = "Reset and seed demo data (members, chores, completion history)."

    def add_arguments(self, parser):
        parser.add_argument("--fresh", action="store_true", help="delete existing data first")

    def handle(self, *args, **options):
        if options["fresh"]:
            Completion.objects.all().delete()
            Chore.objects.all().delete()
            Member.objects.all().delete()

        if Member.objects.exists():
            self.stdout.write(self.style.WARNING("Data already present — use --fresh to reset."))
            return

        members = [Member.objects.create(name=n, email=e) for n, e in MEMBERS]
        today = timezone.localdate()
        random.seed(7)

        for i, (name, desc, rec, diff, offset) in enumerate(CHORES):
            chore = Chore.objects.create(
                name=name, description=desc, recurrence=rec, difficulty=diff,
                assigned_to=members[i % len(members)],
                due_date=today + timedelta(days=offset),
            )
            # backfill some history so the leaderboard and stats look alive
            for k in range(random.randint(1, 5)):
                Completion.objects.create(
                    chore=chore,
                    completed_by=random.choice(members),
                    points_awarded=chore.points,
                    was_late=random.random() < 0.25,
                    note=random.choice(["", "", "took a while", "all done", "needed extra soap"]),
                )

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(members)} members, {len(CHORES)} chores, "
            f"{Completion.objects.count()} completions."))
