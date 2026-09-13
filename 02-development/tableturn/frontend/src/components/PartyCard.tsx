import { useState } from "react";

import type { CancelReason, Party } from "../api/types";
import {
  CANCEL_REASONS,
  formatClock,
  formatEstimate,
  formatWaitSoFar,
  guestLabel,
} from "../lib/format";

interface PartyCardProps {
  party: Party;
  onSeat: (party: Party) => void;
  onCancel: (party: Party, reason: CancelReason) => void;
  onDelete: (party: Party) => void;
  disabled?: boolean;
}

/** One row of the waiting list (US-2). */
export function PartyCard({ party, onSeat, onCancel, onDelete, disabled = false }: PartyCardProps) {
  // Local to the card so choosing a reason on one row does not change others.
  const [reason, setReason] = useState<CancelReason>("no_show");
  const isNext = party.position === 1;

  return (
    <li className={`party ${isNext ? "party--next" : ""}`} data-testid="party-card">
      <div className="party__position" aria-hidden="true">
        {party.position ?? "–"}
      </div>

      <div className="party__body">
        <div className="party__heading">
          <h3 className="party__name">{party.name}</h3>
          <span className="party__size">{guestLabel(party.party_size)}</span>
          {isNext ? <span className="pill pill--accent">Next up</span> : null}
        </div>

        <p className="party__meta">
          <span className="party__estimate">{formatEstimate(party.estimated_wait_minutes)}</span>
          <span aria-hidden="true">·</span>
          <span>{formatWaitSoFar(party.created_at)}</span>
          <span aria-hidden="true">·</span>
          <span>added {formatClock(party.created_at)}</span>
        </p>

        {party.phone ? <p className="party__note">📞 {party.phone}</p> : null}
        {party.notes ? <p className="party__note">📝 {party.notes}</p> : null}
      </div>

      <div className="party__actions">
        <button
          className="btn btn--primary"
          type="button"
          onClick={() => onSeat(party)}
          disabled={disabled}
        >
          Seat
        </button>

        <div className="party__cancel">
          <select
            aria-label={`Cancel reason for ${party.name}`}
            value={reason}
            onChange={(event) => setReason(event.target.value as CancelReason)}
            disabled={disabled}
          >
            {CANCEL_REASONS.map((entry) => (
              <option key={entry.value} value={entry.value}>
                {entry.label}
              </option>
            ))}
          </select>
          <button
            className="btn btn--ghost"
            type="button"
            onClick={() => onCancel(party, reason)}
            disabled={disabled}
          >
            Cancel
          </button>
        </div>

        <button
          className="btn btn--icon"
          type="button"
          aria-label={`Remove ${party.name} from the list`}
          title="Delete (data-entry mistake)"
          onClick={() => onDelete(party)}
          disabled={disabled}
        >
          ✕
        </button>
      </div>
    </li>
  );
}
