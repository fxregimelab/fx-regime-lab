"use client";

import { ToastItem } from "./toast";
import { useToast } from "./toast-context";

/** Global toast container — positioned top-right, max 3 stacked.
 *  Rendered once in root layout.
 */
export function Toaster() {
  const { toasts, removeToast } = useToast();

  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed top-4 right-4 z-[var(--z-toast)] flex flex-col gap-2 w-[320px] max-w-[calc(100vw-2rem)]"
      aria-live="polite"
      aria-atomic="true"
    >
      {toasts.map((toast) => (
        <ToastItem
          key={toast.id}
          id={toast.id}
          message={toast.message}
          type={toast.type}
          onDismiss={removeToast}
        />
      ))}
    </div>
  );
}
