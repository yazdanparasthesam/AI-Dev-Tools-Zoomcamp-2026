# Backlog

Ordered, each task independently shippable.

## Task 1: Set up the Django project skeleton
Create the `config` project and the `chores` app, register `chores` in `INSTALLED_APPS`
in `settings.py`, wire `config/urls.py` to the app's URLs, add the SPA shell template,
and verify `manage.py migrate` and `manage.py runserver` work.

## Task 2: Member model + API
`Member` model (name, email, colour, is_active) with derived `points`/`initials`,
migration, DRF serializer and `MemberViewSet` with CRUD, admin registration.

## Task 3: Chore model + API
`Chore` model (name, description, recurrence, assignment_mode, assigned_to,
difficulty, due_date, is_active) with derived `points`/`status`/`days_until_due`,
serializer with validation, `ChoreViewSet` with CRUD and query filters.

## Task 4: Completion, rotation and scheduling
`Completion` log model. `Chore.mark_done()` — log the completion with points and a
late flag, roll the due date forward (catching up if badly overdue), rotate to the
next active member unless the chore is in `keep` mode. Expose as
`POST /api/chores/:id/done/`, plus a `snooze` action.

## Task 5: Aggregate endpoints
`GET /api/dashboard/` returning status buckets, leaderboard, recent activity and
headline counters in one round-trip. `GET /api/stats/` with per-member and per-chore
breakdowns and an overall late rate.

## Task 6: Frontend SPA
Vanilla-JS single-page app served as Django static files: dashboard, chores, members,
history and stats screens, modal create/edit forms, toasts, dark responsive theme.

## Task 7: Tests and seed data
Model tests (due-date rollover per recurrence, overdue catch-up, rotation wrap-around,
inactive-member skipping, keep mode, zero-member safety) and API tests (CRUD,
validation errors, done/snooze actions, aggregate payload shapes, read-only history).
A `seed` management command for reproducible demo data.
