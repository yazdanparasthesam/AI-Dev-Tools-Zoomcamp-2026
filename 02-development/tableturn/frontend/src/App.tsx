import { useCallback, useEffect, useState } from "react";

import {
  API_BASE_URL,
  cancelParty,
  createParty,
  createTable,
  deleteParty,
  deleteTable,
  freeTable,
  seatParty,
  updateTable,
} from "./api/client";
import type {
  CancelReason,
  Party,
  PartyCreate,
  Table,
  TableCreate,
  TableUpdate,
} from "./api/types";
import { FloorPanel } from "./components/FloorPanel";
import { HistoryPanel } from "./components/HistoryPanel";
import { SeatDialog } from "./components/SeatDialog";
import { StatsBar } from "./components/StatsBar";
import { Toast } from "./components/Toast";
import type { ToastMessage } from "./components/Toast";
import { WaitlistPanel } from "./components/WaitlistPanel";
import { useWaitlistData } from "./hooks/useWaitlistData";

export default function App() {
  const [seatingParty, setSeatingParty] = useState<Party | null>(null);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<ToastMessage | null>(null);

  // Polling pauses while the seat dialog is open (spec §9 / AGENTS.md).
  const { parties, tables, stats, loading, connectionError, refresh } = useWaitlistData(
    seatingParty !== null,
  );

  const notify = useCallback((kind: ToastMessage["kind"], text: string) => {
    setToast({ id: Date.now(), kind, text });
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 4500);
    return () => clearTimeout(timer);
  }, [toast]);

  /** Run a mutation, refresh, and report the outcome. Returns success. */
  const run = useCallback(
    async (action: () => Promise<unknown>, successMessage: string): Promise<boolean> => {
      setBusy(true);
      try {
        await action();
        await refresh();
        notify("success", successMessage);
        return true;
      } catch (error) {
        notify("error", error instanceof Error ? error.message : "Something went wrong");
        return false;
      } finally {
        setBusy(false);
      }
    },
    [notify, refresh],
  );

  const handleAddParty = useCallback(
    async (payload: PartyCreate) => {
      await run(() => createParty(payload), `${payload.name} added — position updated`);
    },
    [run],
  );

  const handleSeat = useCallback(
    async (party: Party, tableId: string) => {
      const table = tables.find((entry) => entry.id === tableId);
      const ok = await run(
        () => seatParty(party.id, tableId),
        `${party.name} seated at ${table?.name ?? "table"}`,
      );
      if (ok) setSeatingParty(null);
    },
    [run, tables],
  );

  const handleCancel = useCallback(
    async (party: Party, reason: CancelReason) => {
      await run(() => cancelParty(party.id, reason), `${party.name} removed from the list`);
    },
    [run],
  );

  const handleDeleteParty = useCallback(
    async (party: Party) => {
      await run(() => deleteParty(party.id), `${party.name} deleted`);
    },
    [run],
  );

  const handleAddTable = useCallback(
    async (payload: TableCreate) => {
      await run(() => createTable(payload), `Table ${payload.name} added`);
    },
    [run],
  );

  const handleTurnTable = useCallback(
    async (table: Table) => {
      await run(() => freeTable(table.id), `${table.name} is free again`);
    },
    [run],
  );

  const handleDeleteTable = useCallback(
    async (table: Table) => {
      await run(() => deleteTable(table.id), `Table ${table.name} deleted`);
    },
    [run],
  );

  const handleUpdateTable = useCallback(
    async (table: Table, payload: TableUpdate) => {
      await run(() => updateTable(table.id, payload), "Table updated");
    },
    [run],
  );

  return (
    <div className="app">
      <header className="app__header">
        <div className="app__title">
          <h1>TableTurn</h1>
          <p className="app__tagline">Host stand · waitlist, floor and shift stats</p>
        </div>
        <div className="app__backend">
          <span className="app__backend-label">Backend</span>
          <code>{API_BASE_URL}</code>
        </div>
      </header>

      {connectionError ? (
        <div className="banner banner--error" role="alert">
          <strong>Backend unreachable.</strong> {connectionError}. Start it with{" "}
          <code>uv run uvicorn backend.app.main:app --reload --port 8000</code>.
        </div>
      ) : null}

      <StatsBar stats={stats} />

      <main className="app__grid">
        <WaitlistPanel
          parties={parties}
          loading={loading}
          disabled={busy}
          onAdd={handleAddParty}
          onSeat={setSeatingParty}
          onCancel={handleCancel}
          onDelete={handleDeleteParty}
        />
        <FloorPanel
          tables={tables}
          parties={parties}
          disabled={busy}
          onAddTable={handleAddTable}
          onTurnTable={handleTurnTable}
          onDeleteTable={handleDeleteTable}
          onUpdateTable={handleUpdateTable}
        />
      </main>

      <HistoryPanel parties={parties} tables={tables} />

      {seatingParty ? (
        <SeatDialog
          party={seatingParty}
          tables={tables}
          busy={busy}
          onConfirm={handleSeat}
          onClose={() => setSeatingParty(null)}
        />
      ) : null}

      <Toast toast={toast} onDismiss={() => setToast(null)} />
    </div>
  );
}
