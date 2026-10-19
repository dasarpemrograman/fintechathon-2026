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
      <summary>Manually add an excerpt, quotation, or rule</summary>
      <p className="muted">
        Preserve the original text, scope, and dates. New evidence remains
        unreviewed. An excerpt hash covers the entered text, not the entire
        website.
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
                "User-entered excerpt; applicability and authenticity require review.",
              ],
              review_status: "unreviewed",
            },
          };
          command(root + "/evidence", body);
        }}
      >
        <label>
          Original document (if already uploaded)
          <select
            value={documentId}
            onChange={(e) => setDocumentId(e.target.value)}
          >
            <option value="">Use a URL & excerpt</option>
            {documents.map((d) => (
              <option key={d.id} value={d.id}>
                {d.filename}
              </option>
            ))}
          </select>
        </label>
        <label>
          Source URL
          <input name="url" type="url" required={!documentId} />
        </label>
        <label>
          Source title
          <input name="title" required />
        </label>
        <label>
          Publisher / quotation provider
          <input name="publisher" required />
        </label>
        <label>
          Language
          <select name="language" defaultValue="en">
            <option value="id">Indonesian</option>
            <option value="en">English</option>
            <option value="zh">中文</option>
            <option value="und">Other / not yet known</option>
          </select>
        </label>
        <label>
          Original excerpt
          <textarea name="claim" rows={5} required />
        </label>
        <label>
          Excerpt location (page / line)
          <input name="locator" required />
        </label>
        <label>
          Scope & applicability reason
          <textarea name="applicability" required />
        </label>
        <div className="grid">
          <label>
            Effective from (if known)
            <input name="effective" type="date" />
          </label>
          <label>
            Valid until (if known)
            <input name="valid_until" type="date" />
          </label>
        </div>
        <button>Save unreviewed evidence</button>
      </form>
    </details>
  );
}
