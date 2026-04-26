export default function Loading() {
  return (
    <div className="mx-auto max-w-[1280px] animate-pulse px-6 py-10">
      <div className="mb-4 h-3 w-24 rounded bg-[#f0f0f0]" />
      <div className="mb-10 h-10 w-64 rounded bg-[#f0f0f0]" />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {[0, 1, 2].map((i) => (
          <div key={i} className="h-48 rounded border border-[#e5e5e5] bg-[#fafafa]" />
        ))}
      </div>
    </div>
  );
}
