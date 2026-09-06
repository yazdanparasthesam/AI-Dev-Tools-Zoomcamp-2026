"""Test suite: models, API endpoints, and rotation/scheduling rules."""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from .models import Chore, Completion, Member


class MemberModelTests(TestCase):
    def test_initials_and_defaults(self):
        m = Member.objects.create(name="Ana Lopez")
        self.assertEqual(m.initials, "AL")
        self.assertTrue(m.is_active)
        self.assertTrue(m.color.startswith("#"))

    def test_points_sum_completions(self):
        m = Member.objects.create(name="Ana")
        c = Chore.objects.create(name="Dishes", difficulty=3, assigned_to=m)
        c.mark_done()
        self.assertEqual(m.points, 30)


class ChoreModelTests(TestCase):
    def setUp(self):
        self.a = Member.objects.create(name="Ana")
        self.b = Member.objects.create(name="Ben")
        self.c = Member.objects.create(name="Chi")
        self.today = timezone.localdate()

    def test_points_scale_with_difficulty(self):
        self.assertEqual(Chore(difficulty=1).points, 10)
        self.assertEqual(Chore(difficulty=5).points, 50)

    def test_status_buckets(self):
        t = self.today
        self.assertEqual(Chore(due_date=t - timedelta(days=2)).status, "overdue")
        self.assertEqual(Chore(due_date=t).status, "today")
        self.assertEqual(Chore(due_date=t + timedelta(days=2)).status, "soon")
        self.assertEqual(Chore(due_date=t + timedelta(days=9)).status, "upcoming")

    def test_mark_done_logs_completion_with_points(self):
        ch = Chore.objects.create(name="Trash", difficulty=2, assigned_to=self.a, due_date=self.today)
        ch.mark_done(note="done")
        comp = Completion.objects.get()
        self.assertEqual(comp.completed_by, self.a)
        self.assertEqual(comp.points_awarded, 20)
        self.assertFalse(comp.was_late)

    def test_late_completion_flagged(self):
        ch = Chore.objects.create(name="Trash", assigned_to=self.a, due_date=self.today - timedelta(days=3))
        ch.mark_done()
        self.assertTrue(Completion.objects.get().was_late)

    def test_due_date_advances_per_recurrence(self):
        for rec, days in Chore.RECURRENCE_DAYS.items():
            ch = Chore.objects.create(name=rec, recurrence=rec, assigned_to=self.a, due_date=self.today)
            ch.mark_done()
            self.assertEqual(ch.due_date, self.today + timedelta(days=days))

    def test_overdue_chore_catches_up_to_future(self):
        ch = Chore.objects.create(name="Trash", recurrence=Chore.DAILY,
                                  assigned_to=self.a, due_date=self.today - timedelta(days=10))
        ch.mark_done()
        self.assertGreaterEqual(ch.due_date, self.today)

    def test_rotation_cycles_all_members(self):
        ch = Chore.objects.create(name="Vacuum", assigned_to=self.a, due_date=self.today)
        for expected in [self.b, self.c, self.a]:
            ch.mark_done()
            self.assertEqual(ch.assigned_to, expected)

    def test_keep_mode_does_not_rotate(self):
        ch = Chore.objects.create(name="Plants", assignment_mode=Chore.KEEP,
                                  assigned_to=self.a, due_date=self.today)
        ch.mark_done()
        self.assertEqual(ch.assigned_to, self.a)

    def test_rotation_skips_inactive_members(self):
        self.b.is_active = False
        self.b.save()
        ch = Chore.objects.create(name="Mop", assigned_to=self.a, due_date=self.today)
        ch.mark_done()
        self.assertEqual(ch.assigned_to, self.c)

    def test_snooze(self):
        ch = Chore.objects.create(name="Mop", due_date=self.today)
        ch.snooze(3)
        self.assertEqual(ch.due_date, self.today + timedelta(days=3))

    def test_no_members_leaves_unassigned(self):
        Member.objects.all().delete()
        ch = Chore.objects.create(name="Solo", due_date=self.today)
        ch.mark_done()
        self.assertIsNone(ch.assigned_to)


class APITests(APITestCase):
    def setUp(self):
        self.a = Member.objects.create(name="Ana")
        self.b = Member.objects.create(name="Ben")
        self.today = timezone.localdate()
        self.chore = Chore.objects.create(name="Dishes", difficulty=3,
                                          assigned_to=self.a, due_date=self.today)

    def test_list_members(self):
        r = self.client.get("/api/members/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.json()), 2)

    def test_create_member(self):
        r = self.client.post("/api/members/", {"name": "Chi"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertTrue(Member.objects.filter(name="Chi").exists())

    def test_create_chore(self):
        r = self.client.post("/api/chores/", {
            "name": "Mop", "recurrence": "weekly", "difficulty": 2,
            "assigned_to": self.a.id, "due_date": str(self.today)}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["points"], 20)

    def test_invalid_difficulty_rejected(self):
        r = self.client.post("/api/chores/", {
            "name": "Bad", "difficulty": 9, "due_date": str(self.today)}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_done_endpoint_rotates_and_logs(self):
        r = self.client.post(f"/api/chores/{self.chore.pk}/done/", {"note": "shiny"}, format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["chore"]["assigned_to_name"], "Ben")
        self.assertEqual(r.json()["completion"]["points_awarded"], 30)
        self.assertEqual(Completion.objects.count(), 1)

    def test_snooze_endpoint(self):
        r = self.client.post(f"/api/chores/{self.chore.pk}/snooze/", {"days": 2}, format="json")
        self.assertEqual(r.json()["due_date"], str(self.today + timedelta(days=2)))

    def test_patch_chore(self):
        r = self.client.patch(f"/api/chores/{self.chore.pk}/", {"name": "Wash up"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.chore.refresh_from_db()
        self.assertEqual(self.chore.name, "Wash up")

    def test_delete_chore(self):
        self.assertEqual(self.client.delete(f"/api/chores/{self.chore.pk}/").status_code, 204)
        self.assertEqual(Chore.objects.count(), 0)

    def test_filter_chores_by_member(self):
        r = self.client.get(f"/api/chores/?member={self.b.id}")
        self.assertEqual(len(r.json()), 0)

    def test_dashboard_payload(self):
        r = self.client.get("/api/dashboard/")
        data = r.json()
        self.assertEqual(r.status_code, 200)
        self.assertIn("buckets", data)
        self.assertEqual(data["stats"]["due_today"], 1)
        self.assertEqual(len(data["leaderboard"]), 2)

    def test_stats_endpoint(self):
        self.chore.mark_done()
        data = self.client.get("/api/stats/").json()
        self.assertEqual(data["by_member"][0]["name"], "Ana")
        self.assertEqual(data["by_member"][0]["points"], 30)

    def test_completions_readonly(self):
        self.assertEqual(self.client.post("/api/completions/", {}, format="json").status_code, 405)

    def test_spa_index_served(self):
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Chore Roster")
