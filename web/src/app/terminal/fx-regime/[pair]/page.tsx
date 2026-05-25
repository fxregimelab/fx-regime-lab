import { redirect } from "next/navigation";

interface RedirectProps {
  params: Promise<{ pair: string }>;
}

export default async function TerminalFxRegimePairRedirectPage({
  params,
}: RedirectProps) {
  const { pair } = await params;
  redirect(`/desk/fx-regime/${pair}`);
}
