/** Display formatting. Pure functions so they are trivially testable. */

export function formatEstimate(minutes: number | null): string {
  if (minutes === null) return "—";
  if (minutes <= 0) return "Seating now";
  return `~${minutes} min wait`;
}

export function formatWaitSoFar(createdAtIso: string, now: Date = new Date()): string {
  const created = new Date(createdAtIso).getTime();
  if (Number.isNaN(created)) return "—";
  const minutes = Math.max(0, Math.floor((now.getTime() - created) / 60_000));
  if (minutes < 1) return "just now";
  if (minutes === 1) return "waiting 1 min";
  return `waiting ${minutes} min`;
}

export function formatClock(iso: string | null): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function guestLabel(size: number): string {
  return size === 1 ? "1 guest" : `${size} guests`;
}

export function tableLabel(capacity: number): string {
  return capacity === 1 ? "1 seat" : `${capacity} seats`;
}

export function minutesLabel(minutes: number): string {
  return minutes === 1 ? "1 min" : `${minutes} min`;
}

export const CANCEL_REASONS = [
  { value: "no_show", label: "No show" },
  { value: "walked", label: "Walked out" },
  { value: "other", label: "Other" },
] as const;

export function cancelReasonLabel(reason: string | null): string {
  if (!reason) return "Cancelled";
  return CANCEL_REASONS.find((entry) => entry.value === reason)?.label ?? "Cancelled";
}
