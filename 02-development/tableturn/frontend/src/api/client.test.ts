import { beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, API_BASE_URL, cancelParty, listParties, seatParty } from "./client";
import type { Party } from "./types";

const PARTY: Party = {
  id: "p1",
  name: "Ava",
  party_size: 4,
  phone: null,
  notes: null,
  status: "waiting",
  created_at: "2026-09-12T18:00:00Z",
  seated_at: null,
  table_id: null,
  cancel_reason: null,
  position: 1,
  estimated_wait_minutes: 0,
};

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("api client", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
  });

  it("defaults the base URL to the local backend", () => {
    // This is the URL the frontend uses to talk to the backend.
    expect(API_BASE_URL).toBe("http://localhost:8000");
  });

  it("calls the backend with the contract path and a JSON body", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, PARTY));

    await seatParty("p1", "t2");

    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://localhost:8000/api/parties/p1/seat");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ table_id: "t2" }));
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
  });

  it("adds the status filter as a query parameter", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, [PARTY]));

    await listParties("waiting");

    expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8000/api/parties?status=waiting");
  });

  it("omits the query parameter when no status is given", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(200, []));

    await listParties();

    expect(fetchMock.mock.calls[0][0]).toBe("http://localhost:8000/api/parties");
  });

  it("surfaces the server's error code and message", async () => {
    fetchMock.mockResolvedValueOnce(
      jsonResponse(409, {
        error: { code: "table_too_small", message: "Table T1 seats 2, but the party has 4 guests" },
      }),
    );

    const error = await seatParty("p1", "t1").catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(409);
    expect((error as ApiError).code).toBe("table_too_small");
    expect((error as ApiError).message).toContain("seats 2");
  });

  it("falls back to FastAPI's detail for validation errors", async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse(422, { detail: "party_size must be >= 1" }));

    const error = await cancelParty("p1").catch((caught: unknown) => caught);

    expect((error as ApiError).code).toBe("http_422");
    expect((error as ApiError).message).toBe("party_size must be >= 1");
  });

  it("resolves to undefined for 204 responses", async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 204 }));

    await expect(cancelParty("p1")).resolves.not.toThrow();
  });

  it("reports an unreachable backend instead of a raw TypeError", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch"));

    const error = await listParties().catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("network_error");
    expect((error as ApiError).message).toContain("Cannot reach the backend");
  });
});
