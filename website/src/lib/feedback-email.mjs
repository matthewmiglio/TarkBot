// The feedback email body. Plain .mjs so the API route and test-email.mjs share
// one template instead of two that drift.
// ponytail: string template, no email framework. It is one table.

const esc = (s) =>
  String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

/** @param {{name?: string, email?: string, message: string, page?: string, sentAt?: string}} f */
export function feedbackHtml(f) {
  const rows = [
    ["From", f.name || "(no name)"],
    ["Reply to", f.email ? `<a href="mailto:${esc(f.email)}">${esc(f.email)}</a>` : "(none given)"],
    ["Page", f.page || "tarkbot.org"],
    ["Sent", f.sentAt ? new Date(f.sentAt).toUTCString() : ""],
  ];
  return `<!doctype html>
<html><body style="margin:0;background:#0d0d0f;padding:32px;font-family:ui-sans-serif,system-ui,Segoe UI,Arial,sans-serif">
  <table role="presentation" width="100%" style="max-width:600px;margin:0 auto;background:#141417;border:1px solid #26262b;border-radius:12px">
    <tr><td style="padding:24px 28px;border-bottom:1px solid #26262b">
      <div style="font-size:11px;letter-spacing:.25em;text-transform:uppercase;color:#7a7a85">Tarkbot</div>
      <div style="margin-top:6px;font-size:20px;color:#f2f2f5">New feedback</div>
    </td></tr>
    <tr><td style="padding:20px 28px">
      <table role="presentation" width="100%" style="font-size:13px;color:#a5a5b0">
        ${rows
          .filter(([, v]) => v)
          .map(
            ([k, v]) =>
              `<tr><td style="padding:4px 12px 4px 0;color:#7a7a85;white-space:nowrap">${k}</td><td style="padding:4px 0;color:#d8d8e0">${k === "Reply to" ? v : esc(v)}</td></tr>`,
          )
          .join("")}
      </table>
    </td></tr>
    <tr><td style="padding:0 28px 28px">
      <div style="background:#0d0d0f;border:1px solid #26262b;border-radius:8px;padding:18px;font-size:14px;line-height:1.6;color:#e4e4ea;white-space:pre-wrap">${esc(f.message)}</div>
    </td></tr>
  </table>
</body></html>`;
}

/** @param {{name?: string, email?: string, message: string, page?: string, sentAt?: string}} f */
export function feedbackText(f) {
  return `New Tarkbot feedback\n\nFrom: ${f.name || "(no name)"}\nReply to: ${f.email || "(none given)"}\nPage: ${f.page || "tarkbot.org"}\n\n${f.message}`;
}
