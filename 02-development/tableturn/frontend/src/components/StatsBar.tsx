import type { Stats } from "../api/types";
import { minutesLabel } from "../lib/format";

interface StatsBarProps {
  stats: Stats | null;
}

interface StatProps {
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "accent" | "warn";
}

function Stat({ label, value, hint, tone = "default" }: StatProps) {
  return (
    <div className={`stat stat--${tone}`}>
      <span className="stat__label">{label}</span>
      <span className="stat__value">{value}</span>
      {hint ? <span className="stat__hint">{hint}</span> : null}
    </div>
  );
}

/** US-7: shift numbers, computed by the backend (rule R9). */
export function StatsBar({ stats }: StatsBarProps) {
  if (!stats) {
    return (
      <div className="stats-bar" aria-busy="true">
        <p className="muted">Loading stats…</p>
      </div>
    );
  }

  return (
    <div className="stats-bar" data-testid="stats-bar">
      <Stat
        label="Waiting"
        value={String(stats.waiting_count)}
        hint={`${stats.covers_waiting} covers`}
        tone="accent"
      />
      <Stat label="Seated" value={String(stats.seated_count)} />
      <Stat label="Completed" value={String(stats.completed_count)} />
      <Stat label="No-shows" value={String(stats.cancelled_count)} tone="warn" />
      <Stat
        label="Longest wait"
        value={minutesLabel(stats.longest_wait_minutes)}
        tone={stats.longest_wait_minutes >= 30 ? "warn" : "default"}
      />
      <Stat label="Average wait" value={minutesLabel(stats.average_wait_minutes)} />
      <Stat
        label="Tables"
        value={`${stats.free_tables} free / ${stats.occupied_tables} busy`}
        hint={`${stats.free_seats} seats free`}
      />
    </div>
  );
}
