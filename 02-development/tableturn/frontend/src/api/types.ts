/**
 * Types mirroring openapi.yaml (the source of truth).
 * If the contract changes, change these first — the compiler will then tell
 * you every place in the UI that needs updating.
 */

export type PartyStatus = "waiting" | "seated" | "completed" | "cancelled";

export type TableStatus = "free" | "occupied";

export type CancelReason = "no_show" | "walked" | "other";

export interface Party {
  id: string;
  name: string;
  party_size: number;
  phone: string | null;
  notes: string | null;
  status: PartyStatus;
  /** ISO-8601 UTC with a Z suffix (rule R10). */
  created_at: string;
  seated_at: string | null;
  table_id: string | null;
  cancel_reason: string | null;
  /** 1-based place in the waiting list; null unless status is "waiting". */
  position: number | null;
  /** (position - 1) * 10; null unless status is "waiting". */
  estimated_wait_minutes: number | null;
}

export interface Table {
  id: string;
  name: string;
  capacity: number;
  status: TableStatus;
  occupied_by_party_id: string | null;
  occupied_since: string | null;
}

export interface Stats {
  waiting_count: number;
  seated_count: number;
  completed_count: number;
  cancelled_count: number;
  covers_waiting: number;
  longest_wait_minutes: number;
  average_wait_minutes: number;
  free_tables: number;
  occupied_tables: number;
  free_seats: number;
}

export interface Health {
  status: string;
  database: string;
}

export interface PartyCreate {
  name: string;
  party_size: number;
  phone?: string | null;
  notes?: string | null;
}

export type PartyUpdate = Partial<Omit<PartyCreate, "name" | "party_size">> & {
  name?: string;
  party_size?: number;
};

export interface TableCreate {
  name: string;
  capacity: number;
}

export type TableUpdate = Partial<TableCreate>;

/** Shape of every domain error response (backend/app/errors.py). */
export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
  };
}
