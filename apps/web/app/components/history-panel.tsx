"use client";

import { useEffect, useState } from "react";
import type { components } from "../../../../packages/contracts/api";

type S = components["schemas"];
type Snapshot = S["Workspace"] | S["Deal"];
type Read = <T>(path: string) => Promise<T>;

const fieldNames: Record<string, string> = {
  product: "Product",
  line_items: "Goods",
  shipments: "Shipment",
  parties: "Parties",
  payment_terms: "Payment terms",
  procurement: "Procurement & production",
  constraints: "Owner constraints",
  planning_inputs: "Exploration assumptions",
  unknowns: "Unknown inputs",
  states: "Deal status",
  archived: "Archive status",
  evidence_ids: "Evidence",
  source_sandbox_revision: "Source exploration revision",
  seller_domicile: "Seller domicile",
  dispatch_country: "Dispatch country",
  destination_country: "Destination country",
  reporting_currency: "Reporting currency",
  owner_timezone: "Timezone",
  business_profile: "Business profile",
  mode: "Mode",
  deal_id: "Linked deal",
  snapshot_hash: "Snapshot hash",
};
const describe = (value: unknown): string => {
  if (value === undefined) return "Not recorded in this revision";
  if (value === null) return "Not yet known";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return typeof value === "object"
    ? JSON.stringify(value, null, 2)
    : String(value);
};
const equal = (left: unknown, right: unknown): boolean => {
  if (left === right) return true;
  if (!left || !right || typeof left !== "object" || typeof right !== "object")
    return false;
  const a = left as Record<string, unknown>,
    b = right as Record<string, unknown>;
  const keys = Object.keys(a);
  return (
    keys.length === Object.keys(b).length &&
    keys.every((key) => Object.hasOwn(b, key) && equal(a[key], b[key]))
  );
};

function RevisionHistory({
  root,
  label,
  read,
}: {
  root: string;
  label: string;
  read: Read;
}) {
  const [items, setItems] = useState<Snapshot[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [before, setBefore] = useState("");
  const [after, setAfter] = useState("");
  const [comparison, setComparison] = useState<[Snapshot, Snapshot] | null>(
    null,
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function load(next?: string) {
    setBusy(true);
    setError("");
    if (!next) setComparison(null);
    try {
      const page = await read<{
        items: Snapshot[];
        next_cursor: string | null;
      }>(
        root +
          "/revisions?limit=25" +
          (next ? "&cursor=" + encodeURIComponent(next) : ""),
      );
      setItems((old) => (next ? [...old, ...page.items] : page.items));
      setCursor(page.next_cursor);
      if (!next && page.items.length) {
        setBefore(String(page.items[0].revision));
        setAfter(String(page.items.at(-1)!.revision));
      }
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    void load();
  }, [root]);
  async function inspect() {
    setBusy(true);
    setError("");
    setComparison(null);
    try {
      const fetchRevision = async (revision: string) => {
        const result = await read<Snapshot | S["DealResult"]>(
          root + "/revisions/" + revision,
        );
        return "deal" in result ? result.deal : result;
      };
      setComparison(
        await Promise.all([fetchRevision(before), fetchRevision(after)]),
      );
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const changed = comparison
    ? Object.keys({ ...comparison[0], ...comparison[1] }).filter(
        (key) =>
          !["revision", "snapshot_hash"].includes(key) &&
          !equal(
            comparison[0][key as keyof Snapshot],
            comparison[1][key as keyof Snapshot],
          ),
      )
    : [];
  return (
    <section aria-label={"Revision history " + label}>
      <h3>Revision {label}</h3>
      <p className="muted">
        Historical snapshots are read-only. Selecting one does not change
        current deal inputs or approvals.
      </p>
      {error && (
        <p className="notice error" role="alert">
          {error}
        </p>
      )}
      {busy && <p role="status">Loading revisions…</p>}
      {!busy && items.length === 0 && !error && <p>No saved revisions yet.</p>}
      {items.length > 0 && (
        <>
          <div className="grid">
            {[
              {
                text: "Earlier revision " + label,
                value: before,
                update: setBefore,
              },
              {
                text: "Comparison revision " + label,
                value: after,
                update: setAfter,
              },
            ].map(({ text, value, update }) => (
              <label key={text}>
                {text}
                <select
                  value={value}
                  disabled={busy}
                  onChange={(event) => {
                    update(event.target.value);
                    setComparison(null);
                  }}
                >
                  {items.map((item) => (
                    <option key={item.revision} value={item.revision}>
                      Revision {item.revision}
                      {item.archived ? " · archived" : ""}
                    </option>
                  ))}
                </select>
              </label>
            ))}
          </div>
          <div className="actions">
            <button
              className="secondary"
              disabled={busy || !before || !after}
              onClick={inspect}
            >
              Compare revisions {label}
            </button>
            {cursor && (
              <button
                className="secondary"
                disabled={busy}
                onClick={() => load(cursor)}
              >
                Load more revisions {label}
              </button>
            )}
            <button className="link" disabled={busy} onClick={() => load()}>
              Refresh revisions {label}
            </button>
          </div>
        </>
      )}
      {comparison && (
        <div aria-label={"Revision comparison " + label}>
          <p>
            Revision {comparison[0].revision} → revision{" "}
            {comparison[1].revision}
          </p>
          {changed.length === 0 ? (
            <p>There are no content changes between the selected revisions.</p>
          ) : (
            <div className="scroll">
              <table>
                <thead>
                  <tr>
                    <th>Section</th>
                    <th>Revision {comparison[0].revision}</th>
                    <th>Revision {comparison[1].revision}</th>
                  </tr>
                </thead>
                <tbody>
                  {changed.map((key) => (
                    <tr key={key}>
                      <td>{fieldNames[key] || key.replaceAll("_", " ")}</td>
                      <td>
                        <pre className="source">
                          {describe(comparison[0][key as keyof Snapshot])}
                        </pre>
                      </td>
                      <td>
                        <pre className="source">
                          {describe(comparison[1][key as keyof Snapshot])}
                        </pre>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {comparison.map((snapshot, index) => (
            <details key={index}>
              <summary>
                Full snapshot {label}, revision {snapshot.revision}
              </summary>
              <p>
                Snapshot hash:{" "}
                <code>{snapshot.snapshot_hash || "Not recorded"}</code>
              </p>
              <pre className="source">{JSON.stringify(snapshot, null, 2)}</pre>
            </details>
          ))}
        </div>
      )}
    </section>
  );
}

export function HistoryPanel({
  workspace,
  deal,
  read,
  date,
}: {
  workspace: S["Workspace"];
  deal: S["Deal"] | null;
  read: Read;
  date: (value: string) => string;
}) {
  const [audit, setAudit] = useState<S["AuditRecord"][]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function load(next?: string) {
    setBusy(true);
    setError("");
    try {
      const page = await read<S["AuditRecordPage"]>(
        "audit?workspace_id=" +
          encodeURIComponent(workspace.id) +
          "&limit=25" +
          (next ? "&cursor=" + encodeURIComponent(next) : ""),
      );
      setAudit((old) => (next ? [...old, ...page.items] : page.items));
      setCursor(page.next_cursor);
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    void load();
  }, [workspace.id, workspace.revision, deal?.revision]);
  const root = deal ? "deals/" + deal.id : "workspaces/" + workspace.id;
  return (
    <section className="card">
      <h2>Change history</h2>
      <p>
        <a href={"/api/gateway/" + root + "/export"}>
          Download snapshots, evidence & history
        </a>
      </p>
      <p className="muted">
        JSON exports contain stored records. A full backup also requires the
        database, original files, and encryption key.
      </p>
      <RevisionHistory
        key={workspace.id + ":" + workspace.revision}
        root={"workspaces/" + workspace.id}
        label={workspace.mode === "sandbox" ? "exploration" : "workspace"}
        read={read}
      />
      {deal && (
        <>
          {deal.source_sandbox_revision && (
            <p>
              Deal origin: exploration revision{" "}
              {deal.source_sandbox_revision.revision}. Original assumptions and
              evidence still require review for the relevant scope.
            </p>
          )}
          <RevisionHistory
            key={deal.id + ":" + deal.revision}
            root={"deals/" + deal.id}
            label="deal"
            read={read}
          />
        </>
      )}
      <h3>This workspace's audit trail</h3>
      {error && (
        <p className="notice error" role="alert">
          {error}
        </p>
      )}
      {busy && <p role="status">Loading change history…</p>}
      {!busy && !error && audit.length === 0 && (
        <p>No audit events for this workspace yet.</p>
      )}
      {[...audit]
        .sort((a, b) => b.created_at.localeCompare(a.created_at))
        .map((record) => (
          <details key={record.id}>
            <summary>
              {record.action} · {date(record.created_at)}
            </summary>
            <p>
              Actor: {record.created_by} · purpose: {record.purpose}
            </p>
            <p>
              Revision {record.expected_revision ?? "—"} →{" "}
              {record.current_revision ?? "—"} ·{" "}
              {record.data_mode === "synthetic_demo"
                ? "Synthetic demo"
                : record.data_mode || "Mode not recorded"}
            </p>
            <p>
              Before hash: <code>{record.before_hash || "—"}</code>
              <br />
              After hash: <code>{record.after_hash || "—"}</code>
            </p>
            {record.request_id && (
              <p>
                Request ID: <code>{record.request_id}</code>
              </p>
            )}
            {record.job_id && (
              <p>
                Job ID: <code>{record.job_id}</code>
              </p>
            )}
          </details>
        ))}
      {cursor && (
        <button
          className="secondary"
          disabled={busy}
          onClick={() => load(cursor)}
        >
          Load more audit events
        </button>
      )}
      <button className="link" disabled={busy} onClick={() => load()}>
        Refresh audit trail
      </button>
    </section>
  );
}
