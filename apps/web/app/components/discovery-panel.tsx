"use client";
import { useState } from "react";
import type { components } from "../../../../packages/contracts/api";
type S = components["schemas"];
export function DiscoveryPanel({
  workspace,
  disabled,
  run,
}: {
  workspace: S["Workspace"];
  disabled: boolean;
  run: (path: string, body: unknown) => Promise<void>;
}) {
  const [preview, setPreview] = useState<S["UsagePreview"] | null>(null),
    [error, setError] = useState("");
  const categories = [
    "requirements",
    "freight",
    "market_price",
    "fx",
    "finance",
  ] as const satisfies readonly S["EvidenceCategory"][];
  return (
    <details className="card">
      <summary>Riset sumber publik menurut produk dan yurisdiksi</summary>
      <p>
        {workspace.execution_scope === "demo"
          ? "Mode demo menggunakan sumber sintetis dan tidak menghubungi penyedia eksternal."
          : "Hanya istilah barang dan yurisdiksi publik yang Anda tinjau dikirim ke penyedia pencarian. Hasil tetap memerlukan tinjauan sumber dan keberlakuan."}
      </p>
      <form
        onChange={() => setPreview(null)}
        onSubmit={async (event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          setError("");
          if (!preview) {
            try {
              const response = await fetch("/api/gateway/usage/preview", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  kind: "discovery",
                  execution:
                    workspace.execution_scope === "demo"
                      ? "deterministic"
                      : "enrich",
                  document_pages: 0,
                }),
              });
              const body = await response.json();
              if (!response.ok)
                throw new Error(body.message || "Pratinjau penggunaan gagal.");
              setPreview(body.result);
            } catch (error) {
              setError((error as Error).message);
            }
            return;
          }
          if (!preview.admitted) return;
          const base = String(form.get("base") || "").trim();
          const quotes = String(form.get("quotes") || "")
            .split(",")
            .map((code) => code.trim())
            .filter(Boolean);
          run("workspaces/" + workspace.id + "/discovery-runs", {
            expected_revision: workspace.revision,
            categories: form.getAll("categories"),
            approved_public_terms: String(form.get("terms") || "")
              .split("\n")
              .map((term) => term.trim())
              .filter(Boolean),
            budget: {
              max_queries: 6,
              max_pages: 10,
              max_actions: 20,
              max_provider_retries: 1,
            },
            ...(base && quotes.length
              ? { fx_base_currency: base, fx_quote_currencies: quotes }
              : {}),
          });
        }}
      >
        <label>
          Istilah produk publik yang disetujui (satu per baris)
          <textarea
            name="terms"
            required={workspace.execution_scope !== "demo"}
            placeholder="green coffee beans wholesale grade"
          />
        </label>
        <p className="muted">
          Jangan masukkan nama pihak, bank, nomor rekening atau isi kontrak
          pribadi. Pertanyaan direncanakan terpisah untuk ekspor asal dan impor
          tujuan.
        </p>
        <fieldset disabled={disabled}>
          <legend>Jenis sumber</legend>
          {categories.map((category) => (
            <label key={category}>
              <input
                type="checkbox"
                name="categories"
                value={category}
                defaultChecked
              />
              {
                {
                  requirements: "Persyaratan resmi",
                  freight: "Logistik dan cakupan penawaran",
                  market_price: "Pembanding grosir tujuan",
                  fx: "Kurs referensi",
                  finance: "Produk pembiayaan",
                }[category]
              }
            </label>
          ))}
        </fieldset>
        <div className="split">
          <label>
            Mata uang dasar untuk riset kurs
            <input name="base" placeholder="USD" maxLength={3} />
          </label>
          <label>
            Mata uang kutipan (pisahkan koma)
            <input name="quotes" placeholder="IDR,EUR" />
          </label>
        </div>
        <p className="muted">
          Kurs referensi tidak membuktikan saldo atau konversi bank. Batas
          riset: 6 permintaan, 10 halaman, 20 tindakan dan satu percobaan ulang
          penyedia.
        </p>
        {error && <p role="alert">{error}</p>}
        {preview && (
          <p role="status">
            {preview.reason} · {preview.expected_runs} jatah riset,{" "}
            {preview.expected_pages} halaman ·{" "}
            {preview.admitted ? "Diizinkan" : "Belum diizinkan"}
          </p>
        )}
        <button disabled={disabled || (!!preview && !preview.admitted)}>
          {preview
            ? "Mulai riset dengan batas ini"
            : "Pratinjau penggunaan riset"}
        </button>
      </form>
    </details>
  );
}
