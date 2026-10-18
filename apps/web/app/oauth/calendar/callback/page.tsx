"use client";

import { useEffect, useRef, useState } from "react";

export default function CalendarCallback() {
  const started = useRef(false);
  const [message, setMessage] = useState("Menyelesaikan otorisasi Google…");
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    const params = new URLSearchParams(window.location.search);
    // Remove the one-time code from browser history before starting the exchange.
    window.history.replaceState(null, "", window.location.pathname);
    if (params.has("error")) {
      setMessage(
        "Otorisasi Google dibatalkan atau ditolak. Tidak ada sinkronisasi yang dijalankan.",
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
        "Callback Google tidak valid. Mulai koneksi lagi dari ruang kerja.",
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
              ? "Sesi berakhir. Masuk kembali, lalu mulai koneksi Google lagi."
              : "Koneksi Google gagal atau permintaan sudah kedaluwarsa. Mulai koneksi lagi dari ruang kerja.",
          );
          return;
        }
        setMessage(
          "Google terhubung. Kembali ke ruang kerja untuk memilih kalender. Belum ada peristiwa yang dikirim.",
        );
      })
      .catch(() =>
        setMessage(
          "Layanan tidak dapat dihubungi. Mulai koneksi Google lagi dari ruang kerja.",
        ),
      );
  }, []);
  return (
    <main>
      <section className="card">
        <h1>Koneksi Google Calendar</h1>
        <p role="status">{message}</p>
        <a href="/">Kembali ke ruang kerja</a>
      </section>
    </main>
  );
}
