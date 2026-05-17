"use client";

import { useEffect, useRef, useState } from "react";

interface ContextMenuItem {
  label: string;
  action: () => void;
  disabled?: boolean;
}

interface ContextMenuProps {
  items: ContextMenuItem[];
  children: React.ReactNode;
}

/**
 * Right-click context menu for data cells.
 * Uses terminal styling, 2px radius.
 */
export function ContextMenu({ items, children }: ContextMenuProps) {
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = () => setOpen(false);
    document.addEventListener("click", close);
    document.addEventListener("scroll", close, true);
    return () => {
      document.removeEventListener("click", close);
      document.removeEventListener("scroll", close, true);
    };
  }, [open]);

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault();
    setPos({ x: e.clientX, y: e.clientY });
    setOpen(true);
  };

  return (
    <div ref={ref} onContextMenu={handleContextMenu} className="contents">
      {children}
      {open && (
        <div
          className="fixed z-[var(--z-popover)] border border-[var(--terminal-border)] bg-[var(--terminal-bg-elevated)] py-1 shadow-lg"
          style={{
            left: pos.x,
            top: pos.y,
            borderRadius: 2,
            minWidth: 180,
          }}
        >
          {items.map((item) => (
            <button
              key={item.label}
              type="button"
              disabled={item.disabled}
              onClick={() => {
                item.action();
                setOpen(false);
              }}
              className={`block w-full text-left px-3 py-1.5 font-mono text-[10px] tracking-wider transition-colors cursor-pointer ${
                item.disabled
                  ? "text-[var(--terminal-fg-dim)] cursor-not-allowed"
                  : "text-[var(--terminal-fg)] hover:bg-[var(--terminal-bg-sunken)]"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
