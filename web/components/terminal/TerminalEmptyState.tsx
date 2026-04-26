export function TerminalEmptyState({ message }: { message: string }) {
  return (
    <div className="border border-[#1e1e1e] bg-[#080808] px-4 py-6 text-center">
      <p className="font-sans text-[13px] text-[#555]">{message}</p>
    </div>
  );
}
