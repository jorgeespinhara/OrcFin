import { useEffect, useId, useRef, type ReactNode } from "react";
import { X } from "lucide-react";

interface ModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  widthClass?: string;
  children: ReactNode;
}

export function Modal({
  open,
  onClose,
  title,
  subtitle,
  widthClass = "w-[480px]",
  children,
}: ModalProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    const handleClose = () => {
      dialog.returnValue = "";
      onClose();
    };
    dialog.addEventListener("close", handleClose);

    // Progressive light-dismiss fallback when closedby="any" is unsupported
    let pressedOutside = false;
    const isOutside = (e: PointerEvent) => {
      const r = dialog.getBoundingClientRect();
      return e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
    };
    const onPointerDown = (e: PointerEvent) => {
      if (!("closedBy" in HTMLDialogElement.prototype)) {
        pressedOutside = isOutside(e);
      }
    };
    const onPointerUp = (e: PointerEvent) => {
      if (!("closedBy" in HTMLDialogElement.prototype) && pressedOutside && isOutside(e)) {
        dialog.close();
      }
    };
    dialog.addEventListener("pointerdown", onPointerDown);
    dialog.addEventListener("pointerup", onPointerUp);

    return () => {
      dialog.removeEventListener("close", handleClose);
      dialog.removeEventListener("pointerdown", onPointerDown);
      dialog.removeEventListener("pointerup", onPointerUp);
    };
  }, [onClose]);

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      className={`orcfin-dialog ${widthClass}`}
      {...({ closedby: "any" } as Record<string, string>)}
    >
      <div className="flex items-start justify-between gap-4 border-b border-[var(--border-subtle)] px-6 py-4">
        <div>
          <h1 id={titleId} className="text-base font-semibold text-[var(--text-primary)]">
            {title}
          </h1>
          {subtitle && (
            <p className="mt-0.5 text-xs text-[var(--text-muted)]">{subtitle}</p>
          )}
        </div>
        <button
          type="button"
          onClick={() => dialogRef.current?.close()}
          aria-label="Fechar"
          className="rounded-lg p-1.5 text-[var(--text-muted)] transition hover:bg-[var(--bg-surface-hover)] hover:text-[var(--text-primary)]"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="overflow-y-auto px-6 py-5">{children}</div>
    </dialog>
  );
}
