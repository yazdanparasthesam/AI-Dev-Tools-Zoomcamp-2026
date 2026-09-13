import { useEffect, useMemo, useState } from "react";

import type { Party, Table } from "../api/types";
import { guestLabel, tableLabel } from "../lib/format";

interface SeatDialogProps {
  party: Party;
  tables: Table[];
  busy: boolean;
  onConfirm: (party: Party, tableId: string) => void;
  onClose: () => void;
}

interface Row {
  table: Table;
  eligible: boolean;
  reason: string | null;
}

/**
 * US-3: seat the party at a table that fits.
 *
 * Rule R3 is enforced in the UI *and* the API: tables that are too small or
 * occupied are shown but disabled, so the host understands why they cannot be
 * picked rather than seeing an empty list.
 */
export function SeatDialog({ party, tables, busy, onConfirm, onClose }: SeatDialogProps) {
  const [selected, setSelected] = useState<string | null>(null);

  const rows = useMemo<Row[]>(() => {
    const mapped = tables.map<Row>((table) => {
      if (table.status === "occupied") {
        return { table, eligible: false, reason: "Occupied" };
      }
      if (table.capacity < party.party_size) {
        return {
          table,
          eligible: false,
          reason: `Too small — ${tableLabel(table.capacity)}`,
        };
      }
      return { table, eligible: true, reason: null };
    });

    return mapped.sort((a, b) => {
      if (a.eligible !== b.eligible) return a.eligible ? -1 : 1;
      if (a.table.capacity !== b.table.capacity) return a.table.capacity - b.table.capacity;
      return a.table.name.localeCompare(b.table.name);
    });
  }, [tables, party.party_size]);

  const eligibleCount = rows.filter((row) => row.eligible).length;

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div
      className="modal__backdrop"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="seat-dialog-title">
        <header className="modal__header">
          <h2 id="seat-dialog-title">Seat {party.name}</h2>
          <button className="btn btn--icon" type="button" aria-label="Close" onClick={onClose}>
            ✕
          </button>
        </header>

        <p className="modal__subtitle">
          {guestLabel(party.party_size)} · {eligibleCount} table
          {eligibleCount === 1 ? "" : "s"} available that fit
        </p>

        {rows.length === 0 ? (
          <p className="empty">No tables yet — add one on the floor panel.</p>
        ) : (
          <ul className="table-picker">
            {rows.map(({ table, eligible, reason }) => (
              <li key={table.id}>
                <button
                  type="button"
                  className={`table-option ${eligible ? "" : "table-option--disabled"} ${
                    selected === table.id ? "table-option--selected" : ""
                  }`}
                  disabled={!eligible || busy}
                  aria-pressed={selected === table.id}
                  onClick={() => setSelected(table.id)}
                >
                  <span className="table-option__name">{table.name}</span>
                  <span className="table-option__meta">
                    {eligible
                      ? `${tableLabel(table.capacity)} · ${table.capacity - party.party_size} spare`
                      : reason}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}

        <footer className="modal__footer">
          <button className="btn btn--ghost" type="button" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button
            className="btn btn--primary"
            type="button"
            disabled={!selected || busy}
            onClick={() => {
              if (selected) onConfirm(party, selected);
            }}
          >
            {busy ? "Seating…" : "Seat party"}
          </button>
        </footer>
      </div>
    </div>
  );
}
