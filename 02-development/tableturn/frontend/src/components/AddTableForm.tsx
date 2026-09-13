import { useState } from "react";
import type { FormEvent } from "react";

import type { TableCreate } from "../api/types";

const MAX_CAPACITY = 20;

interface AddTableFormProps {
  onSubmit: (payload: TableCreate) => Promise<void>;
  disabled?: boolean;
}

/** US-6: keep the floor plan matching reality. */
export function AddTableForm({ onSubmit, disabled = false }: AddTableFormProps) {
  const [name, setName] = useState("");
  const [capacity, setCapacity] = useState("4");
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = name.trim();
    const parsed = Number(capacity);

    if (!trimmed) {
      setError("Table name is required");
      return;
    }
    if (!Number.isInteger(parsed) || parsed < 1 || parsed > MAX_CAPACITY) {
      setError(`Capacity must be between 1 and ${MAX_CAPACITY}`);
      return;
    }

    setError(null);
    void onSubmit({ name: trimmed, capacity: parsed }).then(() => {
      setName("");
      setCapacity("4");
    });
  }

  return (
    <form className="form form--inline" onSubmit={handleSubmit} aria-label="Add a table">
      <input
        value={name}
        onChange={(event) => setName(event.target.value)}
        placeholder="Patio 4"
        maxLength={60}
        aria-label="Table name"
        disabled={disabled}
      />
      <input
        type="number"
        min={1}
        max={MAX_CAPACITY}
        value={capacity}
        onChange={(event) => setCapacity(event.target.value)}
        aria-label="Table capacity"
        disabled={disabled}
      />
      <button className="btn btn--ghost" type="submit" disabled={disabled}>
        Add table
      </button>
      {error ? (
        <p className="form__error" role="alert">
          {error}
        </p>
      ) : null}
    </form>
  );
}
