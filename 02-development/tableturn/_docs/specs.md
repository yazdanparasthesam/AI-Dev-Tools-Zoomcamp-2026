# TableTurn — Product Spec

**App name:** TableTurn
**One-liner:** A host-side waitlist manager for restaurants: add parties to the list, see who is next, seat them at a table, and turn tables — with live wait estimates and end-of-shift stats.

**Stack:** React + TypeScript (Vite) frontend, FastAPI backend, SQLite via SQLAlchemy.
**Contract:** `openapi.yaml` at the repo root is the source of truth for the API.

---

## 1. Problem

A busy host stand runs on a paper list or a whiteboard. Parties get added out of
order, nobody knows the real wait time, the host forgets who was seated where,
and at the end of the night there is no record of covers or average wait.

TableTurn replaces the paper list with one shared screen at the host stand.

## 2. Goals

1. A host can add a party to the waitlist in under 10 seconds.
2. The list always shows the correct order and a per-party wait estimate.
3. Seating a party is one action, and it is impossible to double-book a table.
4. Table status is visible at a glance: which tables are free, which are
   occupied, and by whom.
5. Data survives a page refresh and a backend restart (SQLite).
6. Shift stats (parties seated, average wait, covers waiting) are computed by the
   backend, not the browser.

## 3. Non-goals

Explicitly **out of scope** for this version:

- No user accounts, roles, or authentication. Single venue, trusted host stand.
- No SMS/push notifications to guests. "Notify" is a host-side visual state only.
- No multi-venue / multi-floor support.
- No reservations (future-dated bookings). Waitlist is walk-ins, now.
- No guest-facing page. Guests do not open the app.
- No reservations-platform integrations (OpenTable, Resy, Toast).
- No real-time sync across browsers via WebSockets. The frontend polls.
- No payments, tips, or menu management.

## 4. Users

| Persona | Description |
| --- | --- |
| **Host** | Stands at the door, owns the waitlist all shift. Primary and effectively only user. |
| **Manager** | Reviews stats at end of shift. Read-only in practice. |

## 5. Domain model

### Party

A group of guests on the waitlist.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string (uuid) | assigned by backend |
| `name` | string, 1–80 chars | required |
| `party_size` | integer, 1–20 | required |
| `phone` | string \| null | optional, free text |
| `notes` | string \| null | optional, e.g. "highchair", "allergy: nuts" |
| `status` | enum | `waiting` \| `seated` \| `completed` \| `cancelled` |
| `created_at` | datetime (UTC) | when added to the list |
| `seated_at` | datetime \| null | when seated |
| `table_id` | string \| null | set when seated, kept after completion |
| `cancel_reason` | string \| null | e.g. `no_show`, `walked`, `other` |
| `position` | integer \| null | 1-based, computed, only for `waiting` parties |
| `estimated_wait_minutes` | integer \| null | computed, only for `waiting` parties |

**Status lifecycle**

```
waiting ──seat──▶ seated ──turn table──▶ completed
   │
   └──cancel──▶ cancelled
```

A party is never deleted by the lifecycle; `DELETE /api/parties/{id}` exists for
fixing data-entry mistakes and removes the row outright.

### Table

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string (uuid) | assigned by backend |
| `name` | string, 1–60 chars | e.g. "T1", "Patio 3" |
| `capacity` | integer, 1–20 | required |
| `status` | enum | `free` \| `occupied` |
| `occupied_by_party_id` | string \| null | |
| `occupied_since` | datetime \| null | |

### Stats

Computed over all parties, aggregated server-side:

`waiting_count`, `seated_count`, `completed_count`, `cancelled_count`,
`covers_waiting` (sum of `party_size` for waiting parties),
`longest_wait_minutes`, `average_wait_minutes`, `free_tables`, `occupied_tables`,
`free_seats`.

## 6. Business rules

R1. The waiting list is ordered by `created_at` ascending, then `id` ascending
    as a deterministic tie-breaker. `position` is the 1-based index in that order.

R2. `estimated_wait_minutes = (position - 1) * MINUTES_PER_PARTY_AHEAD`, where
    `MINUTES_PER_PARTY_AHEAD = 10`. Position 1 therefore has an estimate of 0
    ("seating now"). The constant is documented here and asserted in tests.

R3. Seating requires: the party is `waiting`, the table exists, the table is
    `free`, and `table.capacity >= party.party_size`. Any failure returns `409`
    with a machine-readable `code` — never a silent success.

R4. Seating sets `party.status = seated`, `party.seated_at = now`,
    `party.table_id = table.id`, `table.status = occupied`,
    `table.occupied_by_party_id = party.id`, `table.occupied_since = now`.

R5. Seating a party recomputes `position` and `estimated_wait_minutes` for every
    remaining waiting party (they all move up one).

R6. Turning a table (`POST /api/tables/{id}/free`) sets the table back to `free`,
    clears `occupied_by_party_id` / `occupied_since`, and moves the occupying
    party to `completed`. Turning an already-free table is a no-op `409`.

R7. Cancelling is only allowed from `waiting`. Cancelling a `seated` party must
    go through turning the table instead.

R8. A table cannot be deleted while `occupied` (`409`); free tables can be
    deleted.

R9. `average_wait_minutes` is the mean of `seated_at - created_at` over parties
    in `seated` or `completed`, in whole minutes, `0` when there are none.

R10. Timestamps are stored and returned in UTC, ISO-8601 with a `Z` suffix. The
     frontend renders them in the browser's local timezone.

## 7. User stories & acceptance criteria

### US-1 — Add a party to the waitlist

> As a host, I want to add a party by name and size so that they are queued in
> the correct order.

**Acceptance criteria**

- Given the waitlist form, when I submit name "Ava" and size 4, then a party
  appears at the end of the waiting list with a `position` and an
  `estimated_wait_minutes`.
- Given an empty name or a size outside 1–20, when I submit, then the request is
  not sent, an inline validation error is shown, and no party is created.
- Given the submit succeeds, when the response arrives, then the form is cleared
  and focus returns to the name field.
- Given `phone` and `notes` are optional, when I leave them empty, then the
  party is still created and the fields are `null`.

### US-2 — See the ordered waitlist

> As a host, I want to see everyone waiting, in order, with wait estimates.

- Given there are waiting parties, when the list renders, then they appear
  ordered by `position` ascending with no gaps (1, 2, 3, …).
- Given a party is seated, when the list refreshes, then the remaining parties'
  positions and estimates are all updated.
- Given the frontend is open, when 5 seconds elapse, then the list is re-fetched
  (polling), so a second host stand sees the same data.
- Given there are no waiting parties, then an empty state is shown instead of a
  blank area.

### US-3 — Seat a party at a table

> As a host, I want to seat the next party at a free table that fits them.

- Given a waiting party of size 4, when I choose it and a free table with
  capacity 4, then the party becomes `seated`, the table becomes `occupied`, and
  the party disappears from the waiting list.
- Given the selected table's capacity is smaller than the party size, then the
  UI disables that table and the API rejects the request with `409`.
- Given the party is already seated, when I attempt to seat it again, then the
  API returns `409` and the UI shows the error without changing state.
- Given seating succeeds, then `seated_at` is set and the stats update.

### US-4 — Turn a table

> As a host, I want to mark a table as cleared so it becomes available again.

- Given an occupied table, when I click "Turn table", then the table is `free`
  and its party is `completed`.
- Given a free table, then the "Turn table" control is not offered.
- Given an occupied table, when I try to delete it, then the API returns `409`.

### US-5 — Cancel / remove a party

> As a host, I want to drop a party that no-showed or walked out.

- Given a waiting party, when I cancel it with reason `no_show`, then it leaves
  the waiting list and `cancelled_count` increments.
- Given a cancelled party, when I view "All today", then it is still visible with
  its reason (an audit trail, not a deletion).

### US-6 — Manage tables

> As a host, I want the floor plan to match reality.

- Given the tables view, when I add a table named "Patio 3" with capacity 6,
  then it appears as `free`.
- Given an existing table, when I rename it or change capacity, then the change
  persists across a refresh.
- Given a duplicate table name, then the API rejects it with `409`.

### US-7 — Shift stats

> As a manager, I want end-of-shift numbers.

- Given the header, then it shows waiting count, covers waiting, seated count,
  average wait, and free/occupied tables.
- Given no seated parties yet, then `average_wait_minutes` is `0`, not `null` or
  `NaN`.

## 8. API surface

All endpoints are under `/api`, except `GET /health`. Errors return
`{"error": {"code": "...", "message": "..."}}`.

| Method | Path | Purpose | Success |
| --- | --- | --- | --- |
| GET | `/health` | liveness | 200 |
| GET | `/api/parties` | list parties, optional `?status=` | 200 |
| POST | `/api/parties` | add party | 201 |
| GET | `/api/parties/{id}` | fetch one | 200 |
| PATCH | `/api/parties/{id}` | edit name/size/phone/notes | 200 |
| POST | `/api/parties/{id}/seat` | seat at `{table_id}` | 200 |
| POST | `/api/parties/{id}/cancel` | cancel with optional `{reason}` | 200 |
| DELETE | `/api/parties/{id}` | hard-delete | 204 |
| GET | `/api/tables` | list tables | 200 |
| POST | `/api/tables` | add table | 201 |
| PATCH | `/api/tables/{id}` | edit name/capacity | 200 |
| POST | `/api/tables/{id}/free` | turn table | 200 |
| DELETE | `/api/tables/{id}` | delete free table | 204 |
| GET | `/api/stats` | shift stats | 200 |

## 9. Frontend behaviour

- **Layout:** left column = waitlist (waiting parties, ordered), right column =
  floor (table grid). Header = stats bar.
- **Seating flow:** click "Seat" on a party → a table picker opens showing only
  tables with `capacity >= party_size` and `status == free`, each labelled with
  remaining seats. Tables that are too small are listed but disabled (so the
  host understands why).
- **All backend calls go through one module:** `frontend/src/api/client.ts`.
  Components never call `fetch` directly. Base URL comes from
  `VITE_API_URL`, defaulting to `http://localhost:8000`.
- **Error handling:** every failed request surfaces a non-blocking toast with
  the server's `message`. No silent failures.
- **Loading & empty states** for every list.
- **Polling:** `GET /api/parties`, `GET /api/tables`, `GET /api/stats` every 5 s.
  Polling pauses while a modal is open so the host's selection cannot vanish.
- **No routing library.** Single screen, three panels.

## 10. Persistence

- SQLAlchemy 2.x ORM, models in `backend/app/models.py`.
- Default URL: `sqlite:///./tableturn.db`, overridable via `DATABASE_URL`.
  Postgres must work by changing only that env var — no code changes, no
  SQLite-specific types.
- The store is behind a `WaitlistStore` protocol. `SqlAlchemyStore` is the only
  implementation, and it is what the API layer depends on — so swapping in a
  different backend means writing one class, not rewriting the routes.
- Tests build the same store against an isolated in-memory SQLite database
  (`sqlite://`) and a fake clock. This replaced the throwaway in-memory mock the
  backend was first developed against (see `docs/ai-usage-report.md`), so the
  rules are tested against the engine that actually ships.
- Tables are created on startup; a small demo seed (4 tables, 3 waiting parties)
  is inserted only when the database is empty and `SEED_DEMO_DATA=true`.

## 11. Testing strategy

| Layer | Location | Tool | Covers |
| --- | --- | --- | --- |
| API / store | `tests/` | pytest + httpx `ASGITransport` | rules R1–R10, status codes, validation, lifecycle |
| Contract | `tests/test_contract.py` | pytest | every path/method in `openapi.yaml` exists in the app and vice versa |
| Frontend logic | `frontend/src/**/*.test.ts(x)` | vitest + React Testing Library | rendering, ordering, validation, seating flow with a mocked client |

Tests must pass against an isolated database; no test may touch the dev
`tableturn.db`.

## 12. Definition of done

- [ ] `README.md` lets a new person run frontend + backend from a clean clone.
- [ ] All 7 user stories demonstrable in the UI.
- [ ] `openapi.yaml` matches the implemented routes (contract test green).
- [ ] Data persists in SQLite across a backend restart.
- [ ] `uv run pytest` and `npm run test` both pass.
