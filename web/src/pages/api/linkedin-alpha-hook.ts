import { truncateLinkedInPost } from "@/lib/linkedin-truncate";
import type { NextApiRequest, NextApiResponse } from "next";

const OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions";
const PRIMARY_MODEL = "google/gemma-3-27b-it:free";

function buildPrompt(cardData: Record<string, unknown>): string {
  const payload = JSON.stringify(cardData);
  const baseUrl = (
    process.env.SITE_PUBLIC_URL || "https://fxregimelab.com"
  ).replace(/\/$/, "");
  return `You are an Institutional FX Strategist. Write a 1,200 character LinkedIn post based on the provided Apex Target data.\nSTRICT CONSTRAINTS:\n- STRICTLY NO MARKETING FLUFF.\n- No emojis.\n- No hashtags.\n- Style: institutional shorthand only (e.g., "1.5x MAD breach," "COT extremes," "Asymmetric Downside").\n- Structure exactly four blocks separated by line breaks:\n  [REGIME NOTE] then [THE NUMBERS] then [THE SQUEEZE RISK] then [LINK]\n- In [LINK], give one plain URL: use pair slug from data (lowercase, e.g. eurusd) as ${baseUrl}/terminal/fx-regime/<slug>\nAPEX_TARGET_JSON:\n${payload}\nOutput: plain text only. Max ~1200 characters. No markdown.`;
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse,
) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const key = process.env.OPENROUTER_API_KEY;
  if (!key) {
    return res.status(503).json({ error: "OPENROUTER_API_KEY not configured" });
  }

  const body = req.body;
  const cardData =
    body && typeof body === "object" && "cardData" in body
      ? (body as { cardData: Record<string, unknown> }).cardData
      : null;

  if (!cardData || typeof cardData !== "object") {
    return res.status(400).json({ error: "Missing cardData object" });
  }

  const routerRes = await fetch(OPENROUTER_URL, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/json",
      "HTTP-Referer": "https://fxregimelab.com",
      "X-Title": "FX Regime Lab",
    },
    body: JSON.stringify({
      model: PRIMARY_MODEL,
      messages: [{ role: "user", content: buildPrompt(cardData) }],
      max_tokens: 520,
      temperature: 0.3,
    }),
  });

  if (!routerRes.ok) {
    const errText = await routerRes.text();
    return res.status(502).json({
      error: "OpenRouter request failed",
      detail: errText.slice(0, 200),
    });
  }

  const data = (await routerRes.json()) as {
    choices?: Array<{ message?: { content?: string | null } }>;
  };
  const raw = data.choices?.[0]?.message?.content?.trim() ?? "";
  if (!raw) {
    return res.status(502).json({ error: "Empty model response" });
  }

  const text = truncateLinkedInPost(raw);
  return res.status(200).json({ text });
}
