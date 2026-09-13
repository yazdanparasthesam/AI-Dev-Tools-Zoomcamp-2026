import type { CancelReason, Party, PartyCreate } from "../api/types";
import { AddPartyForm } from "./AddPartyForm";
import { PartyCard } from "./PartyCard";

interface WaitlistPanelProps {
  parties: Party[];
  loading: boolean;
  disabled?: boolean;
  onAdd: (payload: PartyCreate) => Promise<void>;
  onSeat: (party: Party) => void;
  onCancel: (party: Party, reason: CancelReason) => void;
  onDelete: (party: Party) => void;
}

export function WaitlistPanel({
  parties,
  loading,
  disabled = false,
  onAdd,
  onSeat,
  onCancel,
  onDelete,
}: WaitlistPanelProps) {
  // The backend already returns the waiting list ordered by position (rule R1);
  // sorting again here keeps the UI correct even if that ever changes.
  const waiting = [...parties]
    .filter((party) => party.status === "waiting")
    .sort((a, b) => (a.position ?? Number.MAX_SAFE_INTEGER) - (b.position ?? Number.MAX_SAFE_INTEGER));

  return (
    <section className="panel" aria-labelledby="waitlist-heading">
      <header className="panel__header">
        <h2 id="waitlist-heading">Waitlist</h2>
        <span className="pill">{waiting.length} waiting</span>
      </header>

      <AddPartyForm onSubmit={onAdd} disabled={disabled} />

      {loading ? (
        <p className="muted" aria-busy="true">
          Loading the waitlist…
        </p>
      ) : waiting.length === 0 ? (
        <p className="empty" data-testid="waitlist-empty">
          Nobody is waiting. Enjoy the quiet.
        </p>
      ) : (
        <ul className="party-list">
          {waiting.map((party) => (
            <PartyCard
              key={party.id}
              party={party}
              onSeat={onSeat}
              onCancel={onCancel}
              onDelete={onDelete}
              disabled={disabled}
            />
          ))}
        </ul>
      )}
    </section>
  );
}
