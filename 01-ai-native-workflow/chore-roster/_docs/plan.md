# Spec: Chore Roster — a shared household chores tracker

## Problem
Housemates forget whose turn it is, the same person ends up doing the unpleasant jobs,
and there's no shared record of what actually got done. Arguments follow.

## Users
One small household (2–6 people) sharing a single instance. No authentication in v1 —
members are records, not login accounts. Trust-based, like the whiteboard it replaces.

## Features (v1)

### 1. Household members
Add, list, deactivate and remove housemates. Each gets an avatar colour. Inactive
members stay in the history but drop out of the rotation.

### 2. Chore catalog
Name, description, recurrence (daily / weekly / every 2 weeks / monthly), a 1–5
difficulty rating that drives points, an assignee, and a due date. Chores can be set to
rotate or to stay with one person permanently.

### 3. Mark done → rotate + reschedule
One click logs a completion (who, when, points, whether it was late), rotates the chore
to the next active member, and rolls the due date forward by the recurrence — catching
up if the chore was badly overdue. A snooze action pushes the date without completing.

### 4. Dashboard, history and fairness stats
Chores bucketed into overdue / due today / next 3 days / later; a points leaderboard;
an append-only completion history; and stats showing points per member, most-completed
chores, and the overall late rate — so "am I doing more than my share?" has an answer.

## Explicitly out of scope (v1)
Authentication and per-user views, multiple households, email/push reminders, chore
swap requests, holiday exceptions, photo proof, mobile app.

## Data model
- `Member(name, email, color, is_active, created_at)`
- `Chore(name, description, recurrence, assignment_mode, assigned_to→Member,
   difficulty, due_date, is_active, created_at)`
- `Completion(chore→Chore, completed_by→Member, completed_at, note,
   points_awarded, was_late)` — append-only

## Architecture decision
Backend is a pure JSON REST API (Django REST Framework); the frontend is a separate
vanilla-JS single-page app served as static files. Decoupled enough to swap the UI or
add a mobile client, with no build step to maintain.

## Tech
Python 3.12+, Django, Django REST Framework, django-cors-headers, SQLite,
vanilla JS + CSS, `uv` for environments, `manage.py test` for tests.
