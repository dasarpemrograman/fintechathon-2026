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
      <summary>Research public sources for your product & route</summary>
      <p>
        {workspace.execution_scope === "demo"
          ? "Demo mode uses synthetic sources without contacting external providers."
          : "Only approved public product and jurisdiction terms are sent to the search provider. Results still require source and applicability review."}
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
                throw new Error(body.message || "Unable to preview usage.");
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
          Approved public product terms (one per line)
          <textarea
            name="terms"
            required={workspace.execution_scope !== "demo"}
            placeholder="green coffee beans wholesale grade"
          />
        </label>
        <p className="muted">
          Exclude private party names, bank details, account numbers, and
          contract text. Research is planned separately for origin exports and
          destination imports.
        </p>
        <fieldset disabled={disabled}>
          <legend>Source categories</legend>
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
                  requirements: "Official requirements",
                  freight: "Logistics & quotation coverage",
                  market_price: "Destination wholesale comparables",
                  fx: "Reference FX rates",
                  finance: "Financing products",
                }[category]
              }
            </label>
          ))}
        </fieldset>
        <div className="split">
          <label>
            Base currency for FX research
            <input name="base" placeholder="USD" maxLength={3} />
          </label>
          <label>
            Quote currencies (comma-separated)
            <input name="quotes" placeholder="IDR,EUR" />
          </label>
        </div>
        <p className="muted">
          Reference rates do not prove a bank balance or executed conversion.
          Research limits: 6 requests, 10 pages, 20 actions, and one provider
          retry.
        </p>
        {error && <p role="alert">{error}</p>}
        {preview && (
          <p role="status">
            {preview.reason} · {preview.expected_runs} research allowance units,{" "}
            {preview.expected_pages} pages ·{" "}
            {preview.admitted ? "Allowed" : "Not yet allowed"}
          </p>
        )}
        <button disabled={disabled || (!!preview && !preview.admitted)}>
          {preview
            ? "Start research within these limits"
            : "Preview research usage"}
        </button>
      </form>
    </details>
  );
}
