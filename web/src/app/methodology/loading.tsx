export default function MethodologyLoading() {
  return (
    <div className="min-h-screen bg-[var(--color-void)] flex items-center justify-center">
      <div className="flex flex-col items-center gap-3">
        <div className="w-6 h-6 border-2 border-[var(--color-border)] border-t-[var(--color-text-muted)] rounded-full animate-spin" />
        <p className="font-mono text-[10px] tracking-widest text-[var(--color-text-muted)]">
          LOADING METHODOLOGY
        </p>
      </div>
    </div>
  );
}
