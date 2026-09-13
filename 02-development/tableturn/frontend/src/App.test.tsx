import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import App from "./App";
import * as client from "./api/client";
import type { Party, Stats, Table } from "./api/types";

vi.mock("./api/client", () => ({
  API_BASE_URL: "http://localhost:8000",
  // Keeps the real constructor shape so tests can build realistic errors.
  ApiError: class ApiError extends Error {
    status: number;
    code: string;
    constructor(status: number, code: string, message: string) {
      super(message);
      this.name = "ApiError";
      this.status = status;
      this.code = code;
    }
  },
  getHealth: vi.fn(),
  listParties: vi.fn(),
  createParty: vi.fn(),
  getParty: vi.fn(),
  updateParty: vi.fn(),
  seatParty: vi.fn(),
  cancelParty: vi.fn(),
  deleteParty: vi.fn(),
  listTables: vi.fn(),
  createTable: vi.fn(),
  updateTable: vi.fn(),
  freeTable: vi.fn(),
  deleteTable: vi.fn(),
  getStats: vi.fn(),
}));

const TABLE_SMALL: Table = {
  id: "t1",
  name: "T1",
  capacity: 2,
  status: "free",
  occupied_by_party_id: null,
  occupied_since: null,
};

const TABLE_FITS: Table = {
  id: "t2",
  name: "T2",
  capacity: 4,
  status: "free",
  occupied_by_party_id: null,
  occupied_since: null,
};

const TABLE_BUSY: Table = {
  id: "t3",
  name: "T3",
  capacity: 6,
  status: "occupied",
  occupied_by_party_id: "p9",
  occupied_since: "2026-09-12T18:10:00Z",
};

const PARTY_FIRST: Party = {
  id: "p1",
  name: "Ava",
  party_size: 4,
  phone: null,
  notes: "window seat if possible",
  status: "waiting",
  created_at: "2026-09-12T18:00:00Z",
  seated_at: null,
  table_id: null,
  cancel_reason: null,
  position: 1,
  estimated_wait_minutes: 0,
};

const PARTY_SECOND: Party = {
  ...PARTY_FIRST,
  id: "p2",
  name: "Marcus",
  party_size: 2,
  notes: null,
  created_at: "2026-09-12T18:10:00Z",
  position: 2,
  estimated_wait_minutes: 10,
};

const STATS: Stats = {
  waiting_count: 2,
  seated_count: 1,
  completed_count: 3,
  cancelled_count: 1,
  covers_waiting: 6,
  longest_wait_minutes: 30,
  average_wait_minutes: 12,
  free_tables: 2,
  occupied_tables: 1,
  free_seats: 6,
};

function mockBackend(parties: Party[] = [PARTY_FIRST, PARTY_SECOND]) {
  vi.mocked(client.listParties).mockResolvedValue(parties);
  vi.mocked(client.listTables).mockResolvedValue([TABLE_SMALL, TABLE_FITS, TABLE_BUSY]);
  vi.mocked(client.getStats).mockResolvedValue(STATS);
}

function cardOf(name: string): HTMLElement {
  const heading = screen.getByRole("heading", { name });
  const card = heading.closest('[data-testid="party-card"]');
  if (!card) throw new Error(`No party card rendered for ${name}`);
  return card as HTMLElement;
}

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockBackend();
  });

  it("renders the waiting list in position order", async () => {
    render(<App />);

    const cards = await screen.findAllByTestId("party-card");

    expect(cards).toHaveLength(2);
    expect(within(cards[0]).getByRole("heading", { name: "Ava" })).toBeInTheDocument();
    expect(within(cards[1]).getByRole("heading", { name: "Marcus" })).toBeInTheDocument();
  });

  it("shows the wait estimate from rule R2 and marks the next party", async () => {
    render(<App />);

    expect(await screen.findByText("Seating now")).toBeInTheDocument();
    expect(screen.getByText("~10 min wait")).toBeInTheDocument();
    expect(screen.getByText("Next up")).toBeInTheDocument();
    expect(screen.getByText(/window seat if possible/)).toBeInTheDocument();
  });

  it("renders the stats bar from the backend", async () => {
    render(<App />);

    const bar = await screen.findByTestId("stats-bar");

    expect(within(bar).getByText("6 covers")).toBeInTheDocument();
    expect(within(bar).getByText("12 min")).toBeInTheDocument();
    expect(within(bar).getByText("2 free / 1 busy")).toBeInTheDocument();
  });

  it("renders the floor with table status", async () => {
    render(<App />);

    const cards = await screen.findAllByTestId("table-card");

    expect(cards).toHaveLength(3);
    expect(screen.getByRole("heading", { name: "T3" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Turn table" })).toBeInTheDocument();
  });

  it("shows an empty state when nobody is waiting", async () => {
    mockBackend([]);

    render(<App />);

    expect(await screen.findByTestId("waitlist-empty")).toBeInTheDocument();
  });

  it("refuses to submit an empty party name", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findAllByTestId("party-card");

    await user.click(screen.getByRole("button", { name: "Add to list" }));

    expect(client.createParty).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent("Name is required");
  });

  it("adds a party through the form", async () => {
    vi.mocked(client.createParty).mockResolvedValue(PARTY_FIRST);
    const user = userEvent.setup();
    render(<App />);
    await screen.findAllByTestId("party-card");

    await user.type(screen.getByLabelText("Name"), "Nina");
    const size = screen.getByRole("spinbutton", { name: /guests/i });
    await user.clear(size);
    await user.type(size, "3");
    await user.click(screen.getByRole("button", { name: "Add to list" }));

    expect(client.createParty).toHaveBeenCalledWith({
      name: "Nina",
      party_size: 3,
      phone: null,
      notes: null,
    });
  });

  it("only offers tables that fit and are free, then seats the party", async () => {
    vi.mocked(client.seatParty).mockResolvedValue({ ...PARTY_FIRST, status: "seated" });
    const user = userEvent.setup();
    render(<App />);
    await screen.findAllByTestId("party-card");

    await user.click(within(cardOf("Ava")).getByRole("button", { name: "Seat" }));

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("Seat Ava")).toBeInTheDocument();

    const t1 = within(dialog).getByRole("button", { name: /T1/ });
    const t2 = within(dialog).getByRole("button", { name: /T2/ });
    const t3 = within(dialog).getByRole("button", { name: /T3/ });

    // Rule R3 mirrored in the UI: too small and occupied are disabled.
    expect(t1).toBeDisabled();
    expect(within(dialog).getByText("Too small — 2 seats")).toBeInTheDocument();
    expect(t3).toBeDisabled();
    expect(within(dialog).getByText("Occupied")).toBeInTheDocument();
    expect(t2).toBeEnabled();

    const confirm = within(dialog).getByRole("button", { name: "Seat party" });
    expect(confirm).toBeDisabled();

    await user.click(t2);
    await user.click(confirm);

    expect(client.seatParty).toHaveBeenCalledWith("p1", "t2");
  });

  it("closes the seat dialog without calling the API", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findAllByTestId("party-card");

    await user.click(within(cardOf("Ava")).getByRole("button", { name: "Seat" }));
    const dialog = await screen.findByRole("dialog");
    await user.click(within(dialog).getByRole("button", { name: "Close" }));

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(client.seatParty).not.toHaveBeenCalled();
  });

  it("cancels a party with the selected reason", async () => {
    vi.mocked(client.cancelParty).mockResolvedValue({ ...PARTY_FIRST, status: "cancelled" });
    const user = userEvent.setup();
    render(<App />);
    await screen.findAllByTestId("party-card");

    const card = cardOf("Marcus");
    await user.selectOptions(within(card).getByLabelText("Cancel reason for Marcus"), "walked");
    await user.click(within(card).getByRole("button", { name: "Cancel" }));

    expect(client.cancelParty).toHaveBeenCalledWith("p2", "walked");
  });

  it("deletes a party from the list", async () => {
    vi.mocked(client.deleteParty).mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<App />);
    await screen.findAllByTestId("party-card");

    await user.click(within(cardOf("Ava")).getByRole("button", { name: "Remove Ava from the list" }));

    expect(client.deleteParty).toHaveBeenCalledWith("p1");
  });

  it("turns a table", async () => {
    vi.mocked(client.freeTable).mockResolvedValue({ ...TABLE_BUSY, status: "free" });
    const user = userEvent.setup();
    render(<App />);
    await screen.findAllByTestId("table-card");

    await user.click(screen.getByRole("button", { name: "Turn table" }));

    expect(client.freeTable).toHaveBeenCalledWith("t3");
  });

  it("surfaces an unreachable backend with the URL it tried", async () => {
    vi.mocked(client.listParties).mockRejectedValue(
      new client.ApiError(0, "network_error", "Cannot reach the backend at http://localhost:8000"),
    );

    render(<App />);

    const banner = await screen.findByRole("alert");
    expect(banner).toHaveTextContent("Backend unreachable");
    expect(banner).toHaveTextContent("http://localhost:8000");
  });

  it("shows the server's message when a mutation fails", async () => {
    vi.mocked(client.cancelParty).mockRejectedValue(
      new client.ApiError(409, "party_not_waiting", "Only a waiting party can do that"),
    );
    const user = userEvent.setup();
    render(<App />);
    await screen.findAllByTestId("party-card");

    await user.click(within(cardOf("Ava")).getByRole("button", { name: "Cancel" }));

    expect(await screen.findByTestId("toast")).toHaveTextContent(
      "Only a waiting party can do that",
    );
  });
});
