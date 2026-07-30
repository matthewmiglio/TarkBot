"use client";

import { useState } from "react";

// ponytail: useState + fetch. No form library for three inputs.

const field =
  "w-full bg-plate border border-line px-4 py-3 text-sm text-ink placeholder:text-ink-faint focus:border-edge focus:outline-none transition-colors";

export function ContactForm() {
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">("idle");

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.currentTarget));
    setState("sending");
    try {
      const res = await fetch("/api/feedback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...data, page: window.location.href }),
      });
      setState(res.ok ? "sent" : "error");
    } catch {
      setState("error");
    }
  }

  if (state === "sent") {
    return (
      <p className="glass mt-10 px-6 py-10 text-center text-ink-dim">
        Sent. Thanks — if you left an email, you&apos;ll get a reply there.
      </p>
    );
  }

  return (
    <form onSubmit={onSubmit} className="mt-10 grid gap-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <input name="name" placeholder="Name (optional)" maxLength={120} className={field} />
        <input
          type="email"
          name="email"
          placeholder="Email (optional, for a reply)"
          maxLength={200}
          className={field}
        />
      </div>
      <textarea
        name="message"
        required
        rows={6}
        maxLength={5000}
        placeholder="Bug, idea, or complaint. Screens and resolution help if it's a bug."
        className={`${field} resize-y`}
      />
      {/* Honeypot. Hidden from people, irresistible to bots. */}
      <input
        name="website"
        tabIndex={-1}
        autoComplete="off"
        aria-hidden="true"
        className="hidden"
      />
      <div className="flex flex-wrap items-center gap-4">
        <button
          type="submit"
          disabled={state === "sending"}
          className="glass px-7 py-3 text-sm uppercase tracking-[0.15em] hover:bg-plate-hot transition-colors disabled:opacity-50"
        >
          {state === "sending" ? "Sending…" : "Send"}
        </button>
        {state === "error" && (
          <span className="text-sm text-warning">
            That didn&apos;t go through. Try again, or ping the Discord.
          </span>
        )}
      </div>
    </form>
  );
}
