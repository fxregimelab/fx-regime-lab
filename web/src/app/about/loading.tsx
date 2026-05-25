export default function AboutLoading() {
  return (
    <div className="min-h-screen bg-[var(--color-void)] pt-24 pb-24">
      <div className="max-w-[800px] mx-auto px-6">
        <div className="animate-pulse h-12 bg-[var(--color-surface)] rounded mb-8" />
        <div className="animate-pulse h-40 bg-[var(--color-surface)] rounded mb-8" />
        <div className="animate-pulse h-40 bg-[var(--color-surface)] rounded" />
      </div>
    </div>
  );
}
