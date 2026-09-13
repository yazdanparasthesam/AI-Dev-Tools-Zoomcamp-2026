/**
 * The ONLY module allowed to talk to the backend.
 *
 * Components import these functions; they never call fetch() and never
 * hardcode a URL (see AGENTS.md). The base URL comes from VITE_API_URL and
 * defaults to http://localhost:8000 — the answer to "which URL does the
 * frontend use to talk to the backend?".
 */

import type {
  CancelReason,
  Health,
  Party,
  PartyCreate,
  PartyStatus,
  PartyUpdate,
  Stats,
  Table,
  TableCreate,
  TableUpdate,
} from "./types";

export const DEFAULT_API_URL = "http://localhost:8000";

function resolveBaseUrl(): string {
  // An empty or whitespace-only VITE_API_URL falls back to the default rather
  // than producing a broken relative base URL.
  const raw = (import.meta.env.VITE_API_URL as string | undefined)?.trim();
  return (raw || DEFAULT_API_URL).replace(/\/+$/, "");
}

export const API_BASE_URL = resolveBaseUrl();

/** A non-2xx response, carrying the server's machine-readable code. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/**
 * Pull a code + message out of whatever the server sent back.
 * Domain errors use {"error": {code, message}}; FastAPI validation errors use
 * {"detail": ...}. Anything else falls back to the HTTP status.
 */
function extractError(body: unknown, status: number): { code: string; message: string } {
  if (isRecord(body)) {
    const error = body.error;
    if (isRecord(error) && typeof error.message === "string") {
      return {
        code: typeof error.code === "string" ? error.code : `http_${status}`,
        message: error.message,
      };
    }
    if (typeof body.detail === "string") {
      return { code: `http_${status}`, message: body.detail };
    }
  }
  return { code: `http_${status}`, message: `Request failed with status ${status}` };
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init.headers ?? {}),
      },
    });
  } catch {
    // Network failure / backend down / CORS rejection.
    throw new ApiError(0, "network_error", `Cannot reach the backend at ${API_BASE_URL}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = null;
    }
  }

  if (!response.ok) {
    const { code, message } = extractError(body, response.status);
    throw new ApiError(response.status, code, message);
  }

  return body as T;
}

function body(payload: unknown): RequestInit {
  return { body: JSON.stringify(payload) };
}

// -- health ----------------------------------------------------------------

export function getHealth(): Promise<Health> {
  return request<Health>("/health");
}

// -- parties ---------------------------------------------------------------

export function listParties(status?: PartyStatus): Promise<Party[]> {
  const query = status ? `?status=${status}` : "";
  return request<Party[]>(`/api/parties${query}`);
}

export function createParty(payload: PartyCreate): Promise<Party> {
  return request<Party>("/api/parties", { method: "POST", ...body(payload) });
}

export function getParty(partyId: string): Promise<Party> {
  return request<Party>(`/api/parties/${encodeURIComponent(partyId)}`);
}

export function updateParty(partyId: string, payload: PartyUpdate): Promise<Party> {
  return request<Party>(`/api/parties/${encodeURIComponent(partyId)}`, {
    method: "PATCH",
    ...body(payload),
  });
}

export function seatParty(partyId: string, tableId: string): Promise<Party> {
  return request<Party>(`/api/parties/${encodeURIComponent(partyId)}/seat`, {
    method: "POST",
    ...body({ table_id: tableId }),
  });
}

export function cancelParty(partyId: string, reason: CancelReason = "other"): Promise<Party> {
  return request<Party>(`/api/parties/${encodeURIComponent(partyId)}/cancel`, {
    method: "POST",
    ...body({ reason }),
  });
}

export function deleteParty(partyId: string): Promise<void> {
  return request<void>(`/api/parties/${encodeURIComponent(partyId)}`, { method: "DELETE" });
}

// -- tables ----------------------------------------------------------------

export function listTables(): Promise<Table[]> {
  return request<Table[]>("/api/tables");
}

export function createTable(payload: TableCreate): Promise<Table> {
  return request<Table>("/api/tables", { method: "POST", ...body(payload) });
}

export function updateTable(tableId: string, payload: TableUpdate): Promise<Table> {
  return request<Table>(`/api/tables/${encodeURIComponent(tableId)}`, {
    method: "PATCH",
    ...body(payload),
  });
}

export function freeTable(tableId: string): Promise<Table> {
  return request<Table>(`/api/tables/${encodeURIComponent(tableId)}/free`, { method: "POST" });
}

export function deleteTable(tableId: string): Promise<void> {
  return request<void>(`/api/tables/${encodeURIComponent(tableId)}`, { method: "DELETE" });
}

// -- stats -----------------------------------------------------------------

export function getStats(): Promise<Stats> {
  return request<Stats>("/api/stats");
}
