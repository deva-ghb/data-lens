import { CircleAlert, CircleCheck, Info, TriangleAlert, X } from "lucide-react";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { Button } from "./Button";
import "./ui.css";

export type ToastTone = "good" | "warning" | "critical" | "neutral";

export type ToastInput = { title: string; body?: string; tone?: ToastTone };

type ToastEntry = ToastInput & { id: number };

const ToastContext = createContext<((toast: ToastInput) => void) | null>(null);

const TONE_ICON = { good: CircleCheck, warning: TriangleAlert, critical: CircleAlert, neutral: Info };

const DISMISS_AFTER_MS = 5000;
const MAX_VISIBLE = 3;

/**
 * Adds a toast, making room by dropping the oldest confirmations first.
 * Problem toasts are never dropped; they stay until a person dismisses them.
 */
function withRoomFor(current: ToastEntry[], next: ToastEntry): ToastEntry[] {
  const list = [...current, next];
  while (list.length > MAX_VISIBLE) {
    const oldest = list.findIndex((toast) => toast.tone !== "critical");
    if (oldest < 0) break;
    list.splice(oldest, 1);
  }
  return list;
}

function ToastItem({ toast, onDismiss }: { toast: ToastEntry; onDismiss: (id: number) => void }) {
  const tone = toast.tone ?? "neutral";
  const Icon = TONE_ICON[tone];
  useEffect(() => {
    // Problems stay until dismissed; confirmations fade on their own.
    if (tone === "critical") return undefined;
    const timer = window.setTimeout(() => onDismiss(toast.id), DISMISS_AFTER_MS);
    return () => window.clearTimeout(timer);
  }, [onDismiss, toast.id, tone]);
  return (
    <div className={`dl-toast dl-toast--${tone}`} role={tone === "critical" ? "alert" : "status"}>
      <span className="dl-toast__icon" aria-hidden="true">
        <Icon />
      </span>
      <div className="dl-toast__text">
        <span className="dl-toast__title">{toast.title}</span>
        {toast.body !== undefined && <span className="dl-toast__body">{toast.body}</span>}
      </div>
      <Button
        variant="ghost"
        size="sm"
        iconOnly
        icon={<X />}
        aria-label="Dismiss"
        className="dl-toast__close"
        onClick={() => onDismiss(toast.id)}
      />
    </div>
  );
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastEntry[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const show = useCallback((toast: ToastInput) => {
    const id = nextId.current;
    nextId.current += 1;
    setToasts((current) => withRoomFor(current, { ...toast, id }));
  }, []);

  const value = useMemo(() => show, [show]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div className="dl-toasts" aria-live="polite">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): (toast: ToastInput) => void {
  const show = useContext(ToastContext);
  if (show === null) {
    throw new Error("useToast must be used inside ToastProvider");
  }
  return show;
}
