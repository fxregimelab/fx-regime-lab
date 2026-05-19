import type { Metadata } from "next";
import { redirect } from "next/navigation";

export const metadata: Metadata = {
  title: "Calendar | FX Regime Lab",
  description:
    "Macro event calendar for FX regime analysis. Central bank meetings, inflation prints, and geopolitical risk events.",
};

export default function CalendarPage() {
  redirect("/terminal/calendar");
}
