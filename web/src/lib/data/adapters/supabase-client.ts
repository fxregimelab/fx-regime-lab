import type { createClient } from "@/lib/supabase/server";

export type TypedSupabaseClient = Awaited<ReturnType<typeof createClient>>;
