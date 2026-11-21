import type { NextApiRequest, NextApiResponse } from "next";

type RetiredRouteResponse = { error: string };

export default function handler(
  req: NextApiRequest,
  res: NextApiResponse<RetiredRouteResponse>,
) {
  res.setHeader("Cache-Control", "no-store, max-age=0");
  res.setHeader("Allow", "POST");

  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  return res.status(410).json({
    error: "This server-generated sharing route has been retired.",
  });
}
