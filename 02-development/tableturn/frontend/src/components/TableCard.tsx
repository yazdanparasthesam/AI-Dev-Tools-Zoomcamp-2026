import { useState } from "react";
import type { FormEvent } from "react";

import type { Table, TableUpdate } from "../api/types";
import { formatClock, tableLabel } from "../lib/format";

interface TableCardProps {
  table: Table;
  occupantName: string | null;
  disabled?: boolean;
  onTurn: (table: Table) => void;
  onDelete: (table: Table) => void;
  onUpdate: (table: Table, payload: TableUpdate) => void;
}

const MAX_CAPACITY = 20;

/** One table on the floor (US-4, US-6). */
export function TableCard({
  table,
  occupantName,
  disabled = false,
  onTurn,
  onDelete,
  onUpdate,
}: TableCardProps) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(table.name);
  const [capacity, setCapacity] = useState(String(table.capacity));
  const [error, setError] = useState<string | null>(null);

  const isOccupied = table.status === "occupied";

  function startEditing() {
    setName(table.name);
    setCapacity(String(table.capacity));
    setError(null);
    setEditing(true);
  }

  function handleSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = name.trim();
    const parsed = Number(capacity);

    if (!trimmed) {
      setError("Name is required");
      return;
    }
    if (!Number.isInteger(parsed) || parsed < 1 || parsed > MAX_CAPACITY) {
      setError(`Capacity must be between 1 and ${MAX_CAPACITY}`);
      return;
    }

    setError(null);
    setEditing(false);
    onUpdate(table, { name: trimmed, capacity: parsed });
  }

  return (
    <li
      className={`table-card ${isOccupied ? "table-card--occupied" : "table-card--free"}`}
      data-testid="table-card"
    >
      {editing ? (
        <form className="table-card__edit" onSubmit={handleSave} aria-label={`Edit ${table.name}`}>
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            maxLength={60}
            aria-label="Table name"
          />
          <input
            type="number"
            min={1}
            max={MAX_CAPACITY}
            value={capacity}
            onChange={(event) => setCapacity(event.target.value)}
            aria-label="Table capacity"
          />
          <div className="table-card__edit-actions">
            <button className="btn btn--primary btn--sm" type="submit">
              Save
            </button>
            <button
              className="btn btn--ghost btn--sm"
              type="button"
              onClick={() => setEditing(false)}
            >
              Cancel
            </button>
          </div>
          {error ? (
            <p className="form__error" role="alert">
              {error}
            </p>
          ) : null}
        </form>
      ) : (
        <>
          <div className="table-card__head">
            <h3 className="table-card__name">{table.name}</h3>
            <span className={`pill ${isOccupied ? "pill--warn" : "pill--ok"}`}>
              {isOccupied ? "Occupied" : "Free"}
            </span>
          </div>

          <p className="table-card__meta">
            {tableLabel(table.capacity)}
            {isOccupied && occupantName ? ` · ${occupantName}` : ""}
            {isOccupied && table.occupied_since ? ` · since ${formatClock(table.occupied_since)}` : ""}
          </p>

          <div className="table-card__actions">
            {isOccupied ? (
              <button
                className="btn btn--primary btn--sm"
                type="button"
                onClick={() => onTurn(table)}
                disabled={disabled}
              >
                Turn table
              </button>
            ) : (
              <button
                className="btn btn--ghost btn--sm"
                type="button"
                onClick={() => onDelete(table)}
                disabled={disabled}
              >
                Delete
              </button>
            )}
            <button
              className="btn btn--ghost btn--sm"
              type="button"
              onClick={startEditing}
              disabled={disabled}
            >
              Edit
            </button>
          </div>
        </>
      )}
    </li>
  );
}
