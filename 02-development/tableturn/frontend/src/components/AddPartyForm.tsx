import { useState } from "react";
import type { FormEvent } from "react";

import type { PartyCreate } from "../api/types";

const MAX_PARTY_SIZE = 20;

interface AddPartyFormProps {
  onSubmit: (payload: PartyCreate) => Promise<void> | void;
  disabled?: boolean;
}

/** US-1: add a party in under 10 seconds, with client-side validation. */
export function AddPartyForm({ onSubmit, disabled = false }: AddPartyFormProps) {
  const [name, setName] = useState("");
  const [size, setSize] = useState("2");
  const [phone, setPhone] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const trimmedName = name.trim();
    const parsedSize = Number(size);

    if (!trimmedName) {
      setError("Name is required");
      return;
    }
    if (!Number.isInteger(parsedSize) || parsedSize < 1 || parsedSize > MAX_PARTY_SIZE) {
      setError(`Party size must be between 1 and ${MAX_PARTY_SIZE}`);
      return;
    }

    setError(null);
    void Promise.resolve(
      onSubmit({
        name: trimmedName,
        party_size: parsedSize,
        phone: phone.trim() ? phone.trim() : null,
        notes: notes.trim() ? notes.trim() : null,
      }),
    ).then(() => {
      // Spec US-1: clear the form and return focus to the name field.
      setName("");
      setSize("2");
      setPhone("");
      setNotes("");
      document.getElementById("party-name")?.focus();
    });
  }

  return (
    <form className="form" onSubmit={handleSubmit} aria-label="Add a party">
      <div className="form__row">
        <label className="field field--grow">
          <span className="field__label">Name</span>
          <input
            id="party-name"
            name="name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Ava"
            maxLength={80}
            autoComplete="off"
            disabled={disabled}
          />
        </label>

        <label className="field field--small">
          <span className="field__label">Guests</span>
          <input
            name="party_size"
            type="number"
            min={1}
            max={MAX_PARTY_SIZE}
            value={size}
            onChange={(event) => setSize(event.target.value)}
            disabled={disabled}
          />
        </label>

        <button className="btn btn--primary" type="submit" disabled={disabled}>
          Add to list
        </button>
      </div>

      <div className="form__row">
        <label className="field">
          <span className="field__label">Phone (optional)</span>
          <input
            name="phone"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            placeholder="+90 555 0100"
            maxLength={40}
            autoComplete="off"
            disabled={disabled}
          />
        </label>

        <label className="field field--grow">
          <span className="field__label">Notes (optional)</span>
          <input
            name="notes"
            value={notes}
            onChange={(event) => setNotes(event.target.value)}
            placeholder="highchair, nut allergy…"
            maxLength={280}
            autoComplete="off"
            disabled={disabled}
          />
        </label>
      </div>

      {error ? (
        <p className="form__error" role="alert">
          {error}
        </p>
      ) : null}
    </form>
  );
}
