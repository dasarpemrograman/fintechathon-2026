"use client";
import { useEffect, useState } from "react";
import type { components } from "../../../../packages/contracts/api";
type S = components["schemas"];
type Command = (
  path: string,
  body: unknown,
  method?: string,
) => Promise<unknown>;
export function CalendarPanel({
  deal,
  milestones,
  demo,
  disabled,
  command,
  run,
}: {
  deal: S["Deal"];
  milestones: S["Milestone"][];
  demo: boolean;
  disabled: boolean;
  command: Command;
  run: (path: string, body: unknown) => Promise<void>;
}) {
  const [connections, setConnections] = useState<S["CalendarConnection"][]>([]),
    [connection, setConnection] = useState(""),
    [selected, setSelected] = useState<string[]>([]),
    [action, setAction] = useState<"insert" | "update" | "delete">("insert"),
    [preview, setPreview] = useState<S["CalendarPreview"] | null>(null),
    [approved, setApproved] = useState(false),
    [error, setError] = useState("");
  const root = "deals/" + deal.id;
  async function refresh() {
    const response = await fetch("/api/gateway/calendar/connections");
    const body = await response.json();
    if (!response.ok)
      throw new Error(body.message || "Tidak dapat membaca koneksi.");
    setConnections(body.result.items);
  }
  useEffect(() => {
    refresh().catch((error) => setError(error.message));
  }, []);
  function invalidate() {
    setPreview(null);
    setApproved(false);
  }
  async function connect() {
    setError("");
    const auth = (await command("calendar/connections", {
      redirect_uri: location.origin + "/oauth/calendar/callback",
    })) as S["CalendarAuthorization"] | null;
    if (!auth) return;
    const connected = (await command("calendar/callback", {
      state: auth.state,
      code: "offline-demo",
    })) as S["CalendarConnection"] | null;
    if (!connected) return;
    await command("calendar/connections/" + connected.id + "/selection", {
      calendar_id: "synthetic-local",
    });
    setConnection(connected.id);
    invalidate();
    await refresh();
  }
  const active = connections.find((c) => c.id === connection);
  return (
    <details className="card">
      <summary>Kalender opsional</summary>
      <p>
        Jadwal internal tetap tersedia tanpa kalender eksternal. Proyeksi hanya
        memuat judul milestone umum dan tanggal yang dipilih, tanpa peserta,
        nilai kontrak atau identitas pihak.
      </p>
      {!demo ? (
        <p>
          Validasi akun Google belum dicatat. Siapkan kredensial dan uji siklus
          akun sebelum mengaktifkan proyeksi langsung.
        </p>
      ) : (
        <>
          <strong>DEMO SINTETIS · tidak ada panggilan Google</strong>
          {error && <p role="alert">{error}</p>}
          <div className="actions">
            <button
              disabled={disabled}
              onClick={() =>
                connect().catch((error) => setError(error.message))
              }
            >
              Hubungkan kalender demo
            </button>
            <button
              className="secondary"
              disabled={disabled}
              onClick={() =>
                refresh().catch((error) => setError(error.message))
              }
            >
              Perbarui status proyeksi
            </button>
          </div>
          <label>
            Koneksi kalender
            <select
              value={connection}
              onChange={(e) => {
                setConnection(e.target.value);
                invalidate();
              }}
            >
              <option value="">Pilih koneksi</option>
              {connections
                .filter((c) => c.data_mode === "synthetic_demo")
                .map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.calendar_id || c.id} · {c.status}
                  </option>
                ))}
            </select>
          </label>
          {active && (
            <>
              <p>
                Status koneksi: {active.status} · {active.data_mode}
              </p>
              {active.status === "connected" && (
                <button
                  disabled={disabled}
                  className="secondary"
                  onClick={async () => {
                    await command(
                      "calendar/connections/" + active.id + "/revoke",
                      {},
                    );
                    invalidate();
                    await refresh();
                  }}
                >
                  Cabut koneksi ini
                </button>
              )}
              {active.owned_events?.map((event) => (
                <div key={event.milestone_id}>
                  <p>
                    {event.milestone_id} · status proyeksi: {event.state}
                  </p>
                  {event.state === "conflict" && (
                    <div className="actions">
                      {(["keep_external", "reapprove_projection"] as const).map(
                        (decision) => (
                          <button
                            key={decision}
                            disabled={disabled}
                            onClick={async () => {
                              await command(root + "/calendar-conflicts", {
                                expected_revision: deal.revision,
                                connection_id: active.id,
                                milestone_id: event.milestone_id,
                                decision,
                              });
                              invalidate();
                              await refresh();
                            }}
                          >
                            {decision === "keep_external"
                              ? "Pertahankan perubahan eksternal"
                              : "Tinjau proyeksi lagi"}
                          </button>
                        ),
                      )}
                    </div>
                  )}
                </div>
              ))}
            </>
          )}
          <fieldset disabled={disabled || active?.status !== "connected"}>
            <legend>Milestone yang diproyeksikan</legend>
            {milestones.map((m) => (
              <label key={m.id}>
                <input
                  type="checkbox"
                  checked={selected.includes(m.id)}
                  onChange={(e) => {
                    setSelected((ids) =>
                      e.target.checked
                        ? [...ids, m.id]
                        : ids.filter((id) => id !== m.id),
                    );
                    invalidate();
                  }}
                />
                {m.kind} · {m.id}
              </label>
            ))}
          </fieldset>
          <label>
            Tindakan proyeksi
            <select
              value={action}
              onChange={(e) => {
                setAction(e.target.value as typeof action);
                invalidate();
              }}
            >
              <option value="insert">Tambah</option>
              <option value="update">Perbarui milik aplikasi</option>
              <option value="delete">Hapus milik aplikasi</option>
            </select>
          </label>
          <button
            disabled={
              disabled || !selected.length || active?.status !== "connected"
            }
            onClick={async () => {
              const value = (await command(root + "/calendar-preview", {
                expected_revision: deal.revision,
                connection_id: connection,
                milestone_ids: selected,
                action,
              })) as S["CalendarPreview"] | null;
              setPreview(value);
              setApproved(false);
            }}
          >
            Pratinjau proyeksi
          </button>
          {preview && (
            <>
              <p>
                Hash proyeksi: <code>{preview.projection_hash}</code>
              </p>
              {preview.events.map((event) => (
                <p key={event.milestone_id}>
                  {event.title} ·{" "}
                  {"date" in event.date ? event.date.date : event.date.instant}{" "}
                  · {event.date.timezone} · {event.action}
                </p>
              ))}
              <button
                disabled={disabled || approved}
                onClick={async () => {
                  const result = await command(root + "/approvals", {
                    expected_revision: deal.revision,
                    purpose: "calendar_write",
                    analysis_hash: preview.projection_hash,
                    artifact_hash: null,
                    evidence_digest: preview.projection_hash,
                    decision: "approved",
                  });
                  if (result) setApproved(true);
                }}
              >
                Setujui hash proyeksi ini
              </button>
              <button
                disabled={disabled || !approved}
                onClick={() =>
                  run(root + "/calendar-sync", {
                    expected_revision: deal.revision,
                    connection_id: connection,
                    approved_projection_hash: preview.projection_hash,
                    milestone_ids: selected,
                    action,
                  })
                }
              >
                Jalankan proyeksi demo yang disetujui
              </button>
              <p>
                Pekerjaan diterima belum berarti efek terkirim. Perbarui status
                proyeksi untuk membaca hasil outbox.
              </p>
            </>
          )}
        </>
      )}
    </details>
  );
}
