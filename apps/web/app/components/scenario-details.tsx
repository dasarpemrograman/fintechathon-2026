"use client";

import { useState } from "react";
import type { components } from "../../../../packages/contracts/api";
import { InputValues } from "./numeric-lineage";

type S = components["schemas"];
type Base = S["InputRevisionResponse"]["result"];
const money = (value: S["Money"] | null | undefined) =>
  value ? value.currency + " " + value.amount : "Belum diketahui";

export function ScenarioDetails({
  analysis,
  root,
  timezone,
}: {
  analysis: S["Analysis"];
  root: string;
  timezone: string;
}) {
  const [scenario, setScenario] = useState<S["Scenario"] | null>(null);
  const [base, setBase] = useState<Base | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function inspect() {
    setLoading(true);
    setError("");
    try {
      const response = await fetch(
        "/api/gateway/" +
          root +
          "/scenarios/" +
          encodeURIComponent(analysis.scenario_id),
      );
      const data = await response.json();
      if (!response.ok)
        throw new Error(data.message || "Skenario tidak dapat dibuka.");
      const selected: S["Scenario"] = data.result;
      const reference = selected.base_revision;
      const original = await fetch(
        "/api/gateway/inputs/" +
          encodeURIComponent(reference.id) +
          "/revisions/" +
          reference.revision,
      );
      const snapshot = await original.json();
      if (!original.ok)
        throw new Error(
          snapshot.message || "Versi dasar skenario tidak tersedia.",
        );
      setScenario(selected);
      setBase(snapshot.result);
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const zone =
    base && "owner_timezone" in base ? base.owner_timezone : timezone;
  const date = (value: string | null) =>
    value
      ? new Intl.DateTimeFormat("id-ID", {
          dateStyle: "medium",
          timeStyle: "short",
          timeZone: zone,
        }).format(new Date(value)) +
        " · " +
        zone
      : "Belum diketahui";
  const cash = analysis.cash_metrics;
  return (
    <div className="scenario-comparison">
      {!scenario && (
        <button className="link" disabled={loading} onClick={inspect}>
          Lihat perubahan, jadwal & risiko
        </button>
      )}
      {loading && <p role="status">Memuat skenario dan versi dasarnya…</p>}
      {error && <p role="alert">{error}</p>}
      {scenario && base && (
        <details open>
          <summary>Perubahan, jadwal & risiko versi ini</summary>
          <p>
            Usulan hipotetis; membuka perbandingan tidak mengubah transaksi atau
            mencatat penerimaan pihak lain.
          </p>
          <p>
            {analysis.current_for_use === false
              ? "Analisis historis: perlu tinjauan ulang sebelum tindakan baru."
              : "Kesiapan tindakan tetap ditentukan oleh gerbang server."}
          </p>
          <p>
            Dasar tersimpan: <code>{scenario.base_revision.id}</code> · revisi{" "}
            {scenario.base_revision.revision}
          </p>
          <h3>Bidang yang berubah</h3>
          {scenario.patches.length === 0 && (
            <p>
              Tidak ada perubahan bidang; opsi pendanaan ditampilkan terpisah.
            </p>
          )}
          {scenario.patches.map((patch, index) => (
            <details key={index}>
              <summary>
                {patch.path} · {patch.reason}
              </summary>
              <div className="split">
                <div>
                  <h4>Nilai sebelum usulan</h4>
                  <div className="source">
                    <InputValues
                      value={
                        (base as unknown as Record<string, unknown>)[
                          patch.path.slice(1)
                        ] ?? null
                      }
                    />
                  </div>
                </div>
                <div>
                  <h4>Nilai sesudah usulan</h4>
                  <div className="source">
                    <InputValues value={patch.value} />
                  </div>
                </div>
              </div>
            </details>
          ))}
          <p>
            Opsi pendanaan tersimpan:{" "}
            {scenario.funding_option_ids.join(", ") || "Tidak ada"}
          </p>
          <p>
            Asumsi tersimpan:{" "}
            {scenario.assumption_ids.join(", ") ||
              "Tidak ada referensi tambahan"}
          </p>
          <h3>Waktu dan sisa risiko</h3>
          <p>Kas minimum terjadi: {date(cash?.minimum_at ?? null)}</p>
          <p>Horizon kewajiban: {date(cash?.horizon_end ?? null)}</p>
          <p>
            Eksposur piutang belum tertagih:{" "}
            {money(analysis.owner_comparison?.buyer_receivable_exposure)}
          </p>
          <p className="muted">
            Valuasi referensi, bukan peluang gagal bayar atau bukti dana
            tersedia.
          </p>
          {!cash || cash.calculation_scope === "known_items_only" ? (
            <p>
              Hanya butir yang diketahui; biaya atau waktu yang belum diketahui
              masih memerlukan tinjauan.
            </p>
          ) : (
            <p>Perhitungan mencakup masukan yang dinyatakan.</p>
          )}
          <h4>Interval kas negatif</h4>
          {cash?.negative_intervals.map((interval, index) => (
            <p key={index}>
              {date(interval.start)} →{" "}
              {interval.end
                ? date(interval.end)
                : "Masih terbuka pada akhir horizon"}
            </p>
          ))}
          {cash?.negative_intervals.length === 0 && (
            <p>Tidak ada interval negatif untuk masukan yang dihitung.</p>
          )}
          {analysis.owner_comparison?.checks
            .filter((check) => check.status !== "satisfied")
            .map((check) => (
              <p key={check.code}>
                <strong>
                  {check.code} · {check.status}
                </strong>
                <br />
                {check.reason}
              </p>
            ))}
          {[...analysis.blockers, ...analysis.warnings].map((issue, index) => (
            <p key={index}>
              <strong>{issue.code}</strong> · {issue.reason}
              <br />
              {issue.required_action}
            </p>
          ))}
          {analysis.unknowns.map((unknown, index) => (
            <p key={index}>
              {unknown.field_path} · {unknown.status} · {unknown.reason}
            </p>
          ))}
          <details>
            <summary>Jadwal arus kas versi ini</summary>
            <div className="scroll">
              <table>
                <thead>
                  <tr>
                    <th>Waktu</th>
                    <th>Arah</th>
                    <th>Jumlah</th>
                    <th>Saldo</th>
                  </tr>
                </thead>
                <tbody>
                  {cash?.event_balances?.map((point, index) => (
                    <tr key={index}>
                      <td>{date(point.at)}</td>
                      <td>{point.direction === "in" ? "Masuk" : "Keluar"}</td>
                      <td>{money(point.amount)}</td>
                      <td>{money(point.balance)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        </details>
      )}
    </div>
  );
}
