// Sends one placeholder feedback email through Resend so the template can be
// eyeballed in a real inbox before the form is wired to it.
// Run from website/: node --env-file=.env.local tests/test-email.mjs
import { feedbackHtml, feedbackText } from "../src/lib/feedback-email.mjs";

const sample = {
  name: "Placeholder Pete",
  email: "pete@example.com",
  message:
    "This is a test of the Tarkbot feedback form.\n\nSecond paragraph, to prove line breaks survive. <script>alert(1)</script> should show as text, not run.",
  page: "https://tarkbot.org/#contact",
  sentAt: new Date().toISOString(),
};

const res = await fetch("https://api.resend.com/emails", {
  method: "POST",
  headers: {
    Authorization: `Bearer ${process.env.RESEND_API_KEY}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    from: `Tarkbot Feedback <${process.env.EMAIL_FROM}>`,
    to: [process.env.EMAIL_DESTINATION],
    reply_to: sample.email,
    subject: `Tarkbot feedback from ${sample.name}`,
    html: feedbackHtml(sample),
    text: feedbackText(sample),
  }),
});

console.log(res.status, await res.text());
if (!res.ok) process.exit(1);
