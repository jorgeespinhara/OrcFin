import { AnimatePresence, motion } from "framer-motion";
import { AlertCircle, CheckCircle2, RotateCcw, X } from "lucide-react";

export interface ToastState {
  id: number;
  message: string;
  kind: "success" | "error";
  actionLabel?: string;
  onAction?: () => void;
}

interface ToastProps {
  toast: ToastState | null;
  onDismiss: () => void;
}

export function Toast({ toast, onDismiss }: ToastProps) {
  return (
    <div className="pointer-events-none fixed right-6 bottom-6 z-50">
      <AnimatePresence mode="wait">
        {toast && (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: 18, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 12, scale: 0.96 }}
            transition={{ type: "spring", stiffness: 420, damping: 32 }}
            className="pointer-events-auto flex min-w-[320px] max-w-[440px] items-center gap-3 rounded-2xl border border-[var(--border-strong)] bg-[var(--bg-elevated)] px-4 py-3 shadow-2xl"
          >
            {toast.kind === "success" ? (
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
            ) : (
              <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
            )}
            <span className="flex-1 text-xs font-medium text-[var(--text-primary)]">
              {toast.message}
            </span>
            {toast.actionLabel && toast.onAction && (
              <button
                type="button"
                onClick={() => {
                  const fn = toast.onAction;
                  onDismiss();
                  fn?.();
                }}
                className="inline-flex items-center gap-1 rounded-lg bg-[var(--accent-soft)] px-2.5 py-1 text-xs font-semibold text-[var(--accent)] transition hover:brightness-110"
              >
                <RotateCcw className="h-3 w-3" />
                {toast.actionLabel}
              </button>
            )}
            <button
              type="button"
              onClick={onDismiss}
              aria-label="Fechar notificação"
              className="rounded-md p-1 text-[var(--text-muted)] transition hover:text-[var(--text-primary)]"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
