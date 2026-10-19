"use client";

import { useEffect, useRef, useState } from "react";

export default function CalendarCallback() {
  const started = useRef(false);
  const [message, setMessage] = useState("Completing Google authorization…");
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const params = new URLSearchParams(window.location.search);
    // Remove the one-time code from browser history before starting the exchange.
    window.history.replaceState(null, "", window.location.pathname);
    if (params.has("error")) {
      setMessage(
        "Google authorization was cancelled or denied. No synchronization was started.",
      );
      return;
    }
    const code = params.get("code"),
      state = params.get("state");
    if (
      !code ||
      !state ||
      code.length > 4096 ||
      state.length > 512 ||
      params.getAll("code").length !== 1 ||
      params.getAll("state").length !== 1
    ) {
      setMessage(
        "Invalid Google callback. Start the connection again from your workspace.",
      );
      return;
    }
    // A cross-site Google navigation does not receive the Strict session cookie.
    // This same-origin fetch after loading the page does; bearer tokens stay server-side.
    fetch("/api/gateway/calendar/callback", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Idempotency-Key": crypto.randomUUID(),
      },
      body: JSON.stringify({ code, state }),
      cache: "no-store",
    })
      .then(async (response) => {
        if (!response.ok) {
          setMessage(
            response.status === 401
              ? "Your session expired. Sign in and start the Google connection again."
              : "The Google connection failed or the request expired. Start the connection again from your workspace.",
          );
          return;
        }
        setMessage(
          "Google connected. Return to your workspace to select a calendar. No events have been sent.",
        );
      })
      .catch(() =>
        setMessage(
          "Unable to reach the service. Start the Google connection again from your workspace.",
        ),
      );
  }, []);
  return (
    <main>
      <section className="card">
        <h1>Google Calendar connection</h1>
        <p role="status">{message}</p>
        <a href="/">Back to workspaces</a>
      </section>
    </main>
  );
}
