"use client";
import { useState } from "react";
import type { components } from "../../../../packages/contracts/api";
type S = components["schemas"];
type Command = (
  path: string,
  body: unknown,
  method?: string,
) => Promise<unknown>;
function Source({ evidence }: { evidence: S["Evidence"][] }) {
  return (
    <label>
      Reviewed supporting evidence
      <select name="evidence" required defaultValue="">
        <option value="" disabled>
          Select evidence
        </option>
        {evidence.map((e) => (
          <option key={e.id} value={e.id}>
            {e.title}
          </option>
        ))}
      </select>
    </label>
  );
}
function Reason() {
  return (
    <label>
      Review reason / notes
      <textarea name="reason" required rows={2} />
    </label>
  );
}
function Amount() {
  return (
    <label>
      Actual amount
      <input
        name="amount"
        inputMode="decimal"
        required
        placeholder="Example: 1500000.50"
      />
    </label>
  );
}
export function ReviewControls({
  deal,
  tab,
  context,
  evidence,
  requirements,
  costs,
  receipts,
  milestones,
  fx,
  command,
  editor,
  finance,
  production,
}: {
  deal: S["Deal"];
  tab: string;
  context: S["ReviewContext"] | null;
  evidence: S["Evidence"][];
  requirements: S["Requirement"][];
  costs: S["CostLine"][];
  receipts: S["Receipt"][];
  milestones: S["Milestone"][];
  fx: S["FxObservation"][];
  command: Command;
  editor: boolean;
  finance: boolean;
  production: boolean;
}) {
  const root = "deals/" + deal.id,
    revision = deal.revision;
  if (!context) return null;
  return (
    <>
      {tab === "Overview" && editor && (
        <Parties deal={deal} evidence={evidence} command={command} />
      )}
      {tab === "Drafts & approvals" && editor && (
        <section className="card">
          <h2>Counterparty acceptance</h2>
          <p className="muted">
            Record evidence of acceptance obtained outside the app. The owner's
            review does not represent other parties.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              const body: S["AgreementRequest"] = {
                expected_revision: revision,
                party_id: String(f.get("party")),
                accepted_revision: revision,
                evidence_ids: [String(f.get("evidence"))],
              };
              command(root + "/agreements", body);
            }}
          >
            <label>
              Party accepting the current terms
              <select name="party">
                {deal.parties
                  .filter((p) => !p.roles.includes("seller"))
                  .map((p) => (
                    <option value={p.id} key={p.id}>
                      {p.display_name}
                    </option>
                  ))}
              </select>
            </label>
            <Source evidence={evidence} />
            <label>
              <span>
                <input type="checkbox" required style={{ width: "auto" }} /> I
                reviewed acceptance evidence for revision {revision}.
              </span>
            </label>
            <button>Record external acceptance</button>
          </form>
        </section>
      )}
      {tab === "Readiness & timeline" && (
        <>
          {editor && (
            <ShipmentEntry deal={deal} evidence={evidence} command={command} />
          )}

          {finance && context.cash_snapshot_hash && (
            <section className="card">
              <h2>Review opening balance</h2>
              <p className="muted">
                Verify evidence of the opening balance and commitments outside
                this deal. This does not record payment or drawdown.
              </p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  const body: S["CashVerificationRequest"] = {
                    expected_revision: revision,
                    cash_snapshot_hash: context.cash_snapshot_hash!,
                    evidence_ids: [String(f.get("evidence"))],
                    reason: String(f.get("reason")),
                  };
                  command(root + "/cash-verifications", body);
                }}
              >
                <Source evidence={evidence} />
                <Reason />
                <button>Verify opening balance sources</button>
              </form>
            </section>
          )}
          {production && (
            <>
              <section className="card">
                <h2>Review requirements</h2>
                {requirements.map((r) => (
                  <details key={r.id}>
                    <summary>{r.category}</summary>
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        const f = new FormData(e.currentTarget);
                        const body: S["RequirementReviewRequest"] = {
                          expected_revision: revision,
                          requirement_id: r.id,
                          applicability: f.get(
                            "applicability",
                          ) as S["Requirement"]["applicability"],
                          fulfillment_status: f.get(
                            "fulfillment",
                          ) as S["Requirement"]["fulfillment_status"],
                          evidence_ids: [String(f.get("evidence"))],
                          reason: String(f.get("reason")),
                        };
                        command(root + "/requirement-reviews", body);
                      }}
                    >
                      <label>
                        Applicability
                        <select
                          name="applicability"
                          defaultValue={r.applicability}
                        >
                          <option value="unresolved">Not confirmed</option>
                          <option value="applies">Applies</option>
                          <option value="not_applicable">
                            Does not apply, with evidence
                          </option>
                        </select>
                      </label>
                      <label>
                        Fulfillment
                        <select
                          name="fulfillment"
                          defaultValue={r.fulfillment_status}
                        >
                          <option value="missing">None yet</option>
                          <option value="submitted">Evidence submitted</option>
                          <option value="verified">Evidence verified</option>
                          <option value="rejected">Rejected</option>
                          <option value="expired">Expired</option>
                        </select>
                      </label>
                      <Source evidence={evidence} />
                      <Reason />
                      <button>Save requirement review</button>
                    </form>
                  </details>
                ))}
              </section>
              <Goods
                deal={deal}
                context={context}
                evidence={evidence}
                command={command}
              />
            </>
          )}
          {editor && (
            <section className="card">
              <h2>Record external shipment activity</h2>
              <p className="muted">
                This record does not book transport or submit documents. If the
                activity occurred while its gate was blocked, record the
                exception reason.
              </p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  const body: S["ShipmentEventRequest"] = {
                    expected_revision: revision,
                    shipment_id: String(f.get("shipment")),
                    kind: f.get("kind") as S["ShipmentEventRequest"]["kind"],
                    occurred_at: new Date(
                      String(f.get("occurred_at")) + "Z",
                    ).toISOString(),
                    evidence_ids: [String(f.get("evidence"))],
                    exception_reason: String(f.get("exception_reason")) || null,
                  };
                  command(root + "/shipment-events", body);
                }}
              >
                <label>
                  Shipment
                  <select name="shipment">
                    {deal.shipments.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.dispatch_country} → {s.destination_country} ·{" "}
                        {s.mode}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Event
                  <select name="kind">
                    <option value="booking">
                      Booking performed outside the app
                    </option>
                    <option value="in_transit">In transit</option>
                    <option value="delivered">Delivered</option>
                    <option value="exception">Exception</option>
                  </select>
                </label>
                <label>
                  Event time (UTC)
                  <input name="occurred_at" type="datetime-local" required />
                </label>
                <Source evidence={evidence} />
                <label>
                  Exception reason if prerequisites are unmet
                  <textarea name="exception_reason" />
                </label>
                <button>Record external event</button>
              </form>
            </section>
          )}
          {(editor || finance || production) && (
            <section className="card">
              <h2>Record an external milestone</h2>
              <p className="muted">
                The internal timeline works without Calendar. Forecast changes
                do not alter fixed commitments.
              </p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  const due = {
                    date: String(f.get("date")),
                    timezone: deal.owner_timezone,
                  };
                  const body: S["MilestoneRequest"] = {
                    expected_revision: revision,
                    milestone_id: null,
                    kind: String(f.get("kind")),
                    schedule: { kind: "fixed", due },
                    date_kind: f.get(
                      "date_kind",
                    ) as S["MilestoneRequest"]["date_kind"],
                    value: due,
                    evidence_ids: f.get("evidence")
                      ? [String(f.get("evidence"))]
                      : [],
                  };
                  command(root + "/milestones", body);
                }}
              >
                <label>
                  Event
                  <select name="kind">
                    <option value="arrival">Estimated arrival</option>
                    <option value="acceptance">Goods acceptance</option>
                    <option value="production_complete">
                      Production complete
                    </option>
                    <option value="delivery">Delivery</option>
                  </select>
                </label>
                <label>
                  Date type
                  <select name="date_kind">
                    <option value="forecast">Forecast</option>
                    <option value="agreed">Agreed</option>
                    <option value="actual">Actual, with evidence</option>
                  </select>
                </label>
                <label>
                  Local date ({deal.owner_timezone})
                  <input name="date" type="date" required />
                </label>
                <Source evidence={evidence} />
                <button>Record milestone</button>
              </form>
            </section>
          )}
        </>
      )}
      {tab === "Cost & margin" && finance && (
        <section className="card">
          <h2>Finalize actual costs</h2>
          <p className="muted">
            An actual replaces the estimate for the same component. The estimate
            and original baseline remain available.
          </p>
          {costs.map((c) => (
            <details key={c.id}>
              <summary>
                {c.component_key} ·{" "}
                {c.actual_amount ? "Actual recorded" : "Not final"}
              </summary>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  const body: S["ActualChargeRequest"] = {
                    expected_revision: revision,
                    cost_line_id: c.id,
                    fx_observation_id: String(f.get("fx")) || null,
                    amount: {
                      amount: String(f.get("amount")),
                      currency: String(f.get("currency")),
                    },
                    evidence_ids: [String(f.get("evidence"))],
                    reason: String(f.get("reason")),
                  };
                  command(root + "/actual-charges", body);
                }}
              >
                <Amount />
                <label>
                  Reviewed executed conversion (required for foreign currency)
                  <select name="fx">
                    <option value="">
                      Not applicable to reporting currency
                    </option>
                    {fx.map((row) => (
                      <option key={row.id} value={row.id}>
                        {row.base_currency} → {row.quote_currency} · {row.rate}{" "}
                        · {row.source_date || row.as_of}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Currency
                  <input
                    name="currency"
                    required
                    defaultValue={
                      c.actual_amount?.currency ||
                      c.estimate.base?.currency ||
                      c.rate?.currency ||
                      deal.reporting_currency
                    }
                  />
                </label>
                <Source evidence={evidence} />
                <Reason />
                <button>Record actual cost</button>
              </form>
            </details>
          ))}
        </section>
      )}
      {tab === "Settlement & closure" && finance && (
        <section className="card">
          <h2>Verify & correct payment evidence</h2>
          <p className="muted">
            Each verification or reversal adds to history. Original evidence
            remains traceable.
          </p>
          {receipts
            .filter(
              (r) =>
                !receipts.some((next) => next.supersedes === r.id) &&
                ["pending", "verified"].includes(r.status),
            )
            .map((r) => (
              <details key={r.id}>
                <summary>
                  {r.received_amount.currency} {r.received_amount.amount} ·{" "}
                  {r.value_date} ·{" "}
                  {r.status === "pending"
                    ? "Awaiting verification"
                    : "Verified"}
                </summary>
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const f = new FormData(e.currentTarget);
                    const at = String(f.get("settled_at") || "");
                    const body: S["ReceiptVerificationRequest"] = {
                      expected_revision: revision,
                      receipt_id: r.id,
                      fx_observation_id: String(f.get("fx")) || null,
                      disposition: f.get(
                        "disposition",
                      ) as S["ReceiptVerificationRequest"]["disposition"],
                      evidence_ids: [String(f.get("evidence"))],
                      reason: String(f.get("reason")),
                      settled_at: at ? new Date(at + "Z").toISOString() : null,
                    };
                    command(root + "/receipt-verifications", body);
                  }}
                >
                  <label>
                    Action
                    <select name="disposition">
                      {r.status === "pending" ? (
                        <>
                          <option value="verified">Verify payment</option>
                          <option value="rejected">Reject evidence</option>
                        </>
                      ) : (
                        <option value="reversed">
                          Reverse verification, with a reason
                        </option>
                      )}
                    </select>
                  </label>
                  <label>
                    Known settlement time (UTC, optional)
                    <input name="settled_at" type="datetime-local" />
                  </label>
                  <label>
                    Reviewed executed conversion (required for foreign currency)
                    <select name="fx">
                      <option value="">
                        Not applicable to reporting currency
                      </option>
                      {fx.map((row) => (
                        <option key={row.id} value={row.id}>
                          {row.base_currency} → {row.quote_currency} ·{" "}
                          {row.rate} · {row.source_date || row.as_of}
                        </option>
                      ))}
                    </select>
                  </label>
                  <Source evidence={evidence} />
                  <Reason />
                  <button>Save payment review</button>
                </form>
              </details>
            ))}
        </section>
      )}
    </>
  );
}
function Goods({
  deal,
  context,
  evidence,
  command,
}: {
  deal: S["Deal"];
  context: S["ReviewContext"];
  evidence: S["Evidence"][];
  command: Command;
}) {
  const [status, setStatus] =
    useState<S["GoodsReview"]["status"]>("evidence_review");
  return (
    <section className="card">
      <h2>Goods inspection & corrections</h2>
      <p className="muted">
        Photos alone cannot establish unmeasured quality. Enter measurements and
        select inspection evidence.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          const source = String(f.get("evidence"));
          const measurements: S["GoodsMeasurement"][] = [];
          if (status === "ready")
            for (const line of deal.line_items) {
              for (const attribute of [
                { name: "quantity", unit: line.unit },
                ...(line.product.attributes || []),
              ]) {
                measurements.push({
                  line_item_id: line.id,
                  attribute: attribute.name,
                  value: String(f.get(line.id + "_" + attribute.name)),
                  unit: attribute.unit,
                  evidence_ids: [source],
                });
              }
            }
          const body: S["GoodsReviewRequest"] = {
            expected_revision: deal.revision,
            shipment_id: null,
            status,
            evidence_ids: [source],
            reason: String(f.get("reason")),
            reviewed_specification_hash: context.specification_hash,
            inspection_basis:
              status === "ready" ? "physical_measurements" : "photos_only",
            measurements,
          };
          command("deals/" + deal.id + "/goods-reviews", body);
        }}
      >
        <label>
          Review outcome
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as typeof status)}
          >
            <option value="evidence_review">Further evidence needed</option>
            <option value="nonconforming">
              Nonconforming; correction needed
            </option>
            <option value="ready">Conforming, based on inspection</option>
          </select>
        </label>
        {status === "ready" &&
          deal.line_items.map((line) => (
            <div key={line.id}>
              <h3>{line.product.description}</h3>
              {[
                { name: "quantity", unit: line.unit },
                ...(line.product.attributes || []),
              ].map((a) => (
                <label key={a.name}>
                  Measured {a.name} ({a.unit})
                  <input name={line.id + "_" + a.name} required />
                </label>
              ))}
            </div>
          ))}
        <Source evidence={evidence} />
        <Reason />
        <button>Save goods inspection</button>
      </form>
    </section>
  );
}

function Parties({
  deal,
  evidence,
  command,
}: {
  deal: S["Deal"];
  evidence: S["Evidence"][];
  command: Command;
}) {
  return (
    <section className="card">
      <h2>Complete counterparty identities</h2>
      <p className="muted">
        Identity or role changes require a new analysis and acceptance of terms.
      </p>
      {deal.parties.map((p) => (
        <details key={p.id}>
          <summary>{p.display_name}</summary>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              const parties = deal.parties.map((row) =>
                row.id === p.id
                  ? {
                      ...row,
                      display_name: String(f.get("name")),
                      legal_name: String(f.get("legal")) || null,
                      country: String(f.get("country")).toUpperCase() || null,
                      evidence_ids: [String(f.get("evidence"))],
                    }
                  : row,
              );
              const body: S["PatchFactsRequest"] = {
                expected_revision: deal.revision,
                patches: [
                  {
                    op: "replace",
                    path: "/parties",
                    value: parties,
                    reason: "Counterparty identity reviewed",
                    evidence_ids: [String(f.get("evidence"))],
                    agreement_required_from: parties.map((p) => p.id),
                  },
                ],
              };
              command("deals/" + deal.id + "/facts", body, "PATCH");
            }}
          >
            <label>
              Display name
              <input name="name" required defaultValue={p.display_name} />
            </label>
            <label>
              Legal entity name
              <input name="legal" defaultValue={p.legal_name || ""} />
            </label>
            <label>
              Country (ISO code)
              <input name="country" defaultValue={p.country || ""} />
            </label>
            <Source evidence={evidence} />
            <button>Save identity</button>
          </form>
        </details>
      ))}
    </section>
  );
}
function ShipmentEntry({
  deal,
  evidence,
  command,
}: {
  deal: S["Deal"];
  evidence: S["Evidence"][];
  command: Command;
}) {
  return (
    <details className="card">
      <summary>Add a shipment & goods allocations</summary>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          const shipment: S["Shipment"] = {
            id: "shipment_" + crypto.randomUUID(),
            lines: deal.line_items
              .filter((l) => f.get(l.id) && f.get(l.id) !== "0")
              .map((l) => ({
                line_item_id: l.id,
                quantity: String(f.get(l.id)),
                unit: l.unit,
              })),
            dispatch_country: String(f.get("dispatch")).toUpperCase(),
            destination_country: String(f.get("destination")).toUpperCase(),
            mode: f.get("mode") as S["Shipment"]["mode"],
            incoterm: String(f.get("incoterm")) || null,
            named_place: String(f.get("place")) || null,
            unknowns: [],
          };
          const body: S["PatchFactsRequest"] = {
            expected_revision: deal.revision,
            patches: [
              {
                op: "replace",
                path: "/shipments",
                value: [...deal.shipments, shipment],
                reason: "Shipment scope updated",
                evidence_ids: [String(f.get("evidence"))],
                agreement_required_from: deal.parties.map((p) => p.id),
              },
            ],
          };
          command("deals/" + deal.id + "/facts", body, "PATCH");
        }}
      >
        <label>
          Dispatch country (ISO)
          <input
            name="dispatch"
            required
            defaultValue={deal.seller_domicile || ""}
          />
        </label>
        <label>
          Destination country (ISO)
          <input name="destination" required />
        </label>
        <label>
          Transport mode
          <select name="mode">
            <option value="sea_lcl">Sea LCL</option>
            <option value="sea_fcl">Sea FCL</option>
            <option value="air">Air</option>
            <option value="road">Road</option>
            <option value="rail">Rail</option>
            <option value="multimodal">Multimodal</option>
          </select>
        </label>
        <label>
          Incoterm (if known)
          <input name="incoterm" />
        </label>
        <label>
          Named place in the terms
          <input name="place" />
        </label>
        {deal.line_items.map((l) => (
          <label key={l.id}>
            Quantity {l.product.description} ({l.unit})
            <input
              name={l.id}
              inputMode="decimal"
              placeholder="Leave blank if not allocated"
            />
          </label>
        ))}
        <Source evidence={evidence} />
        <button>Add shipment</button>
      </form>
    </details>
  );
}
