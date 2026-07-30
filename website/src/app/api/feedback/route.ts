import type { NextRequest } from "next/server";
import { feedbackHtml, feedbackText } from "@/lib/feedback-email.mjs";

// Contact form: store the row first (durable), then email it. Same raw-fetch
// Supabase approach as the analytics route, service key server-side only.
// ponytail: no zod, no resend sdk. Three fields and two POSTs.

const SUPABASE_URL = process.env.SUPABASE_URL;
const SERVICE_KEY = process.env.SUPABASE_SERVICE_KEY;
const RESEND_API_KEY = process.env.RESEND_API_KEY;
const EMAIL_FROM = process.env.EMAIL_FROM;
const EMAIL_DESTINATION = process.env.EMAIL_DESTINATION;

export async function POST(req: NextRequest) {
  let body: Record<string, unknown>;
  try {
    body = await req.json();
  } catch {
    return Response.json({ error: "bad json" }, { status: 400 });
  }

  // Honeypot: real people never fill a field they cannot see.
  if (typeof body.website === "string" && body.website) {
    return Response.json({ success: true });
  }

  const str = (v: unknown, max: number) =>
    typeof v === "string" && v.trim() ? v.trim().slice(0, max) : null;

  const message = str(body.message, 5000);
  if (!message) return Response.json({ error: "message required" }, { status: 400 });

  const email = str(body.email, 200);
  if (email && !/^[^@\s]+@[^@\s.]+\.[^@\s]+$/.test(email)) {
    return Response.json({ error: "bad email" }, { status: 400 });
  }

  const fields = {
    name: str(body.name, 120) ?? undefined,
    email: email ?? undefined,
    message,
    page: str(body.page, 300) ?? undefined,
    sentAt: new Date().toISOString(),
  };

  if (SUPABASE_URL && SERVICE_KEY) {
    const res = await fetch(`${SUPABASE_URL}/rest/v1/Tarkbot_feedback`, {
      method: "POST",
      headers: {
        apikey: SERVICE_KEY,
        Authorization: `Bearer ${SERVICE_KEY}`,
        "Content-Type": "application/json",
        Prefer: "return=minimal",
      },
      body: JSON.stringify({
        name: fields.name ?? null,
        email: fields.email ?? null,
        message,
        page: fields.page ?? null,
        ua: req.headers.get("user-agent")?.slice(0, 1024) ?? null,
        country: req.headers.get("x-vercel-ip-country"),
      }),
    });
    if (!res.ok) {
      console.error("feedback insert failed", res.status, await res.text());
      return Response.json({ error: "could not save" }, { status: 502 });
    }
  }

  if (RESEND_API_KEY && EMAIL_FROM && EMAIL_DESTINATION) {
    const res = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${RESEND_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        from: `Tarkbot Feedback <${EMAIL_FROM}>`,
        to: [EMAIL_DESTINATION],
        ...(fields.email ? { reply_to: fields.email } : {}),
        subject: `Tarkbot feedback from ${fields.name ?? fields.email ?? "anonymous"}`,
        html: feedbackHtml(fields),
        text: feedbackText(fields),
      }),
    });
    // The row is already saved, so a mail failure is not the sender's problem.
    if (!res.ok) console.error("feedback email failed", res.status, await res.text());
  }

  return Response.json({ success: true });
}
