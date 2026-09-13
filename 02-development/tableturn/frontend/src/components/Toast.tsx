export interface ToastMessage {
  id: number;
  kind: "success" | "error";
  text: string;
}

interface ToastProps {
  toast: ToastMessage | null;
  onDismiss: () => void;
}

/** Every failed request surfaces here — no silent failures (spec §9). */
export function Toast({ toast, onDismiss }: ToastProps) {
  if (!toast) return null;

  return (
    <div
      className={`toast toast--${toast.kind}`}
      role={toast.kind === "error" ? "alert" : "status"}
      data-testid="toast"
    >
      <span className="toast__text">{toast.text}</span>
      <button className="btn btn--icon btn--sm" type="button" aria-label="Dismiss" onClick={onDismiss}>
        ✕
      </button>
    </div>
  );
}
