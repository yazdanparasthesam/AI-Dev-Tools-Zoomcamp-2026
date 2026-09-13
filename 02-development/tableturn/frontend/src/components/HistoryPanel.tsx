import type { Party, Table } from "../api/types";
import { cancelReasonLabel, formatClock, guestLabel } from "../lib/format";

interface HistoryPanelProps {
  parties: Party[];
  tables: Table[];
}

const STATUS_LABEL: Record<string, string> = {
  seated: "Seated",
  completed: "Completed",
  cancelled: "Cancelled",
};

/** Audit trail: seated and closed parties stay visible (US-5). */
export function HistoryPanel({ parties, tables }: HistoryPanelProps) {
  const tableNameById = new Map(tables.map((table) => [table.id, table.name]));

  const history = parties
    .filter((party) => party.status !== "waiting")
    .sort((a, b) => {
      const left = a.seated_at ?? a.created_at;
      const right = b.seated_at ?? b.created_at;
      return right.localeCompare(left);
    })
    .slice(0, 8);

  if (history.length === 0) return null;

  return (
    <section className="panel panel--wide" aria-labelledby="history-heading">
      <header className="panel__header">
        <h2 id="history-heading">Recent</h2>
        <span className="pill">last {history.length}</span>
      </header>

      <ul className="history">
        {history.map((party) => (
          <li className="history__row" key={party.id} data-testid="history-row">
            <span className={`pill pill--${party.status === "seated" ? "accent" : "muted"}`}>
              {STATUS_LABEL[party.status] ?? party.status}
            </span>
            <span className="history__name">{party.name}</span>
            <span className="history__meta">{guestLabel(party.party_size)}</span>
            {party.table_id ? (
              <span className="history__meta">
                {party.status === "seated" ? "at" : "was at"}{" "}
                {tableNameById.get(party.table_id) ?? "a removed table"}
              </span>
            ) : null}
            {party.status === "cancelled" ? (
              <span className="history__meta">{cancelReasonLabel(party.cancel_reason)}</span>
            ) : null}
            {party.seated_at ? (
              <span className="history__meta">seated {formatClock(party.seated_at)}</span>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
