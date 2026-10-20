"use client";

import { useState } from "react";
import type { components } from "../../../../packages/contracts/api";

type S = components["schemas"];
type Input = S["InputRevisionResponse"]["result"];

// Preserve source strings, native units and nulls. Never recalculate in the browser.
export function InputValues({ value }: { value: unknown }) {
  if (value === null) return <span>Belum diketahui</span>;
  if (Array.isArray(value))
    return value.length ? (
      <ol>
        {value.map((item, index) => (
          <li key={index}>
            <InputValues value={item} />
          </li>
        ))}
      </ol>
    ) : (
      <span>Tidak ada</span>
    );
  if (typeof value === "object")
    return (
      <dl>
        {Object.entries(value as Record<string, unknown>).map(([key, item]) => (
          <div key={key}>
            <dt>{key.replaceAll("_", " ")}</dt>
            <dd>
              <InputValues value={item} />
            </dd>
          </div>
        ))}
      </dl>
    );
  return <span>{String(value)}</span>;
}

export function NumericLineage({
  analysis,
  workspaceId,
}: {
  analysis: S["Analysis"];
  workspaceId: string;
}) {
  const [source, setSource] = useState<Input | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function inspect(ref: S["Ref"]) {
    setLoading(true);
    setError("");
    setSource(null);
    try {
      const response = await fetch(
        "/api/gateway/inputs/" +
          encodeURIComponent(ref.id) +
          "/revisions/" +
          ref.revision,
      );
      const data = await response.json();
      if (!response.ok)
        throw new Error(data.message || "Versi sumber tidak dapat dibuka.");
      setSource(data.result);
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <details className="numeric-lineage">
      <summary>Telusuri rumus dan versi sumber</summary>
      {analysis.numeric_lineage?.map((line, index) => (
        <article key={index}>
          <h3>{line.metric.replaceAll("_", " ")}</h3>
          <p>{line.formula}</p>
          <small>{line.calculator_version}</small>
          <div className="actions">
            {line.evidence_refs.map((ref) => (
              <button
                key={ref.id}
                className="link"
                disabled={loading}
                onClick={() => inspect(ref)}
              >
                Sumber revisi {ref.revision} · {ref.id.slice(-8)}
              </button>
            ))}
          </div>
          <details>
            <summary>{line.input_refs.length} masukan versi tetap</summary>
            <div className="actions">
              {line.input_refs.map((ref) => (
                <button
                  key={ref.id}
                  className="link"
                  disabled={loading}
                  onClick={() => inspect(ref)}
                >
                  Masukan revisi {ref.revision} · {ref.id}
                </button>
              ))}
            </div>
          </details>
        </article>
      ))}
      {!analysis.numeric_lineage && (
        <p className="muted">
          Hitung ulang untuk mendapatkan referensi versi sumber.
        </p>
      )}
      {loading && <p role="status">Memuat versi sumber…</p>}
      {error && <p role="alert">{error}</p>}
      {source && (
        <aside className="source" aria-label="Versi sumber tersimpan">
          <h3>Versi sumber tersimpan</h3>
          <p className="muted">
            Status dan nilai saat analisis dibuat; perubahan berikutnya tidak
            menimpa versi ini. Tinjauan historis tidak memberi izin tindakan
            baru.
          </p>
          {"claim" in source && (
            <>
              <strong>{source.title}</strong>
              <blockquote>{source.claim}</blockquote>
              <p>
                {source.mode} · {source.review_status} · {source.locator}
              </p>
              <p>
                Berlaku hingga: {source.valid_until || "Belum dikonfirmasi"}
              </p>
              <p>{source.limitations.join(" · ")}</p>
              <code>{source.content_hash}</code>
              {source.document_id && (
                <p>
                  <a
                    href={
                      "/api/gateway/workspaces/" +
                      workspaceId +
                      "/documents/" +
                      source.document_id +
                      "/content"
                    }
                    download
                  >
                    Unduh sumber asli
                  </a>
                </p>
              )}
            </>
          )}
          <details>
            <summary>Nilai masukan dan metadata versi ini</summary>
            <InputValues value={source} />
          </details>
        </aside>
      )}
    </details>
  );
}
