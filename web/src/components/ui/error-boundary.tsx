"use client";

import React from "react";

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/** React Error Boundary for data-fetching sections.
 *  Catches render errors and shows a terminal-styled fallback.
 */
export class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.props.onError?.(error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return <DefaultErrorFallback error={this.state.error} />;
    }
    return this.props.children;
  }
}

function DefaultErrorFallback({ error }: { error: Error | null }) {
  return (
    <div className="border border-[var(--terminal-danger)] bg-[var(--terminal-bg)] p-6 font-mono">
      <p className="text-[10px] tracking-widest text-[var(--terminal-danger)] uppercase mb-2">
        [ RENDER ERROR ]
      </p>
      <p className="text-[11px] text-[var(--terminal-fg)] mb-2">
        {error?.message || "Component failed to render."}
      </p>
      <button
        type="button"
        onClick={() => window.location.reload()}
        className="border border-[var(--terminal-border-bright)] bg-transparent px-3 py-1.5 text-[10px] tracking-widest text-[var(--terminal-fg-muted)] hover:text-[var(--terminal-fg)] transition-colors"
      >
        [ RELOAD PAGE ]
      </button>
    </div>
  );
}
