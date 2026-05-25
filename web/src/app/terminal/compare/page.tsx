"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";

export default function TerminalCompareRedirectPage() {
  const router = useRouter();
  const searchParams = useSearchParams();

  useEffect(() => {
    const pairs = searchParams?.get("pairs");
    const query = pairs ? `?pairs=${encodeURIComponent(pairs)}` : "";
    router.replace(`/desk/compare${query}`);
  }, [router, searchParams]);

  return null;
}
