"use client";
import { useState } from "react";
import type { components } from "../../../../packages/contracts/api";
type S = components["schemas"];
export function SourceEntry({
  workspace,
  root,
  revision,
  documents,
  command,
}: {
  workspace: S["Workspace"];
  root: string;
  revision: number;
  documents: S["Document"][];
  command: (path: string, body: unknown, method?: string) => Promise<unknown>;
}) {
  const [documentId, setDocumentId] = useState("");
  return (
    <details className="card">
      <summary>Tambahkan kutipan, penawaran, atau aturan secara manual</summary>
      <p className="muted">
        Simpan teks asli, cakupan dan tanggalnya. Bukti baru tetap belum
        ditinjau. Hash kutipan hanya mencakup teks yang dimasukkan, bukan
        seluruh situs.
      </p>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          const claim = String(f.get("claim"));
          const original = documents.find((d) => d.id === documentId);
          const contentHash =
            original?.content_hash ||
            Array.from(
              new Uint8Array(
                await crypto.subtle.digest(
                  "SHA-256",
                  new TextEncoder().encode(claim),
                ),
              ),
            )
              .map((v) => v.toString(16).padStart(2, "0"))
              .join("");
          const body: S["EvidenceIngestRequest"] = {
            expected_revision: revision,
            evidence: {
              canonical_url: String(f.get("url")) || null,
              document_id: documentId || null,
              publisher: String(f.get("publisher")),
              title: String(f.get("title")),
              language: String(f.get("language")),
              retrieved_at: new Date().toISOString(),
              published_at: null,
              effective_from: String(f.get("effective")) || null,
              valid_until: String(f.get("valid_until")) || null,
              access: "success",
              mode:
                workspace.execution_scope === "demo"
                  ? "synthetic_demo"
                  : "user_provided",
              content_hash: contentHash,
              hash_scope: original ? "original_document" : "manual_excerpt",
              locator: String(f.get("locator")),
              claim,
              applicability: {
                jurisdictions: [
                  workspace.seller_domicile,
                  workspace.destination_country,
                ].filter((v): v is string => !!v),
                product_attributes: [],
                shipment_ids: [],
                line_item_ids: [],
                validity_reason: String(f.get("applicability")),
                unknowns: [],
              },
              limitations: [
                "Kutipan dimasukkan pengguna; keberlakuan dan keaslian perlu ditinjau.",
              ],
              review_status: "unreviewed",
            },
          };
          command(root + "/evidence", body);
        }}
      >
        <label>
          Dokumen asli (jika sudah diunggah)
          <select
            value={documentId}
            onChange={(e) => setDocumentId(e.target.value)}
          >
            <option value="">Gunakan URL dan kutipan</option>
            {documents.map((d) => (
              <option key={d.id} value={d.id}>
                {d.filename}
              </option>
            ))}
          </select>
        </label>
        <label>
          URL sumber
          <input name="url" type="url" required={!documentId} />
        </label>
        <label>
          Judul sumber
          <input name="title" required />
        </label>
        <label>
          Penerbit / pemberi penawaran
          <input name="publisher" required />
        </label>
        <label>
          Bahasa
          <select name="language">
            <option value="id">Indonesia</option>
            <option value="en">English</option>
            <option value="zh">中文</option>
            <option value="und">Lainnya / belum diketahui</option>
          </select>
        </label>
        <label>
          Kutipan asli
          <textarea name="claim" rows={5} required />
        </label>
        <label>
          Lokasi kutipan (halaman / baris)
          <input name="locator" required />
        </label>
        <label>
          Cakupan dan alasan keberlakuan
          <textarea name="applicability" required />
        </label>
        <div className="grid">
          <label>
            Berlaku sejak (jika diketahui)
            <input name="effective" type="date" />
          </label>
          <label>
            Berlaku sampai (jika diketahui)
            <input name="valid_until" type="date" />
          </label>
        </div>
        <button>Simpan bukti belum ditinjau</button>
      </form>
    </details>
  );
}
