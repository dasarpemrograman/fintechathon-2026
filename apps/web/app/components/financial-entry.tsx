"use client";
import { useState } from "react";
import type { components } from "../../../../packages/contracts/api";
type S = components["schemas"];
type Command = (
  path: string,
  body: unknown,
  method?: string,
) => Promise<unknown>;
export function Input({
  name,
  label,
  type = "text",
  value,
  required = true,
  step,
}: {
  name: string;
  label: string;
  type?: string;
  value?: string;
  required?: boolean;
  step?: string;
}) {
  return (
    <label>
      {label}
      <input
        name={name}
        type={type}
        defaultValue={value}
        required={required}
        step={step}
      />
    </label>
  );
}
export function Sources({
  evidence,
  name = "evidence",
  label = "Reviewed evidence",
}: {
  evidence: S["Evidence"][];
  name?: string;
  label?: string;
}) {
  return (
    <label>
      {label}
      <select name={name} required defaultValue="">
        <option value="" disabled>
          Select evidence
        </option>
        {evidence.map((row) => (
          <option key={row.id} value={row.id}>
            {row.title}
          </option>
        ))}
      </select>
    </label>
  );
}
export function Party({
  deal,
  name,
  label,
}: {
  deal: S["Deal"];
  name: string;
  label: string;
}) {
  return (
    <label>
      {label}
      <select name={name} required defaultValue="">
        <option value="" disabled>
          Select a party
        </option>
        {deal.parties.map((row) => (
          <option key={row.id} value={row.id}>
            {row.display_name}
          </option>
        ))}
      </select>
    </label>
  );
}
export function FinancialEntry({
  deal,
  evidence,
  obligations,
  costs,
  fx,
  command,
  finance = true,
  showCosts = true,
}: {
  deal: S["Deal"];
  evidence: S["Evidence"][];
  obligations: S["Obligation"][];
  costs: S["CostLine"][];
  fx: S["FxObservation"][];
  command: Command;
  finance?: boolean;
  showCosts?: boolean;
}) {
  const root = "deals/" + deal.id;
  const [kind, setKind] = useState<S["SettlementAdjustment"]["kind"]>("fee");
  return (
    <>
      {finance && (
        <details className="card">
          <summary>Record an evidenced FX rate</summary>
          <p>
            One unit of the base currency equals this rate in the quote
            currency. For actuals, select evidence of an executed bank
            conversion. A reference rate does not prove available funds.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              const observation: S["FxInput"] = {
                base_currency: String(f.get("base")).toUpperCase(),
                quote_currency: String(f.get("quote")).toUpperCase(),
                rate: String(f.get("rate")),
                as_of: new Date(String(f.get("at")) + "Z").toISOString(),
                evidence_ids: [String(f.get("evidence"))],
                mode:
                  deal.execution_scope === "demo"
                    ? "synthetic_demo"
                    : "user_provided",
              };
              command(root + "/fx-observations", {
                expected_revision: deal.revision,
                observation,
              });
            }}
          >
            <Input name="base" label="FX base currency" />
            <Input
              name="quote"
              label="FX quote currency"
              value={deal.reporting_currency}
            />
            <Input name="rate" label="Rate per base currency unit" />
            <Input
              name="at"
              type="datetime-local"
              label="Known FX time (UTC)"
            />
            <Sources evidence={evidence} />
            <button disabled={!evidence.length}>Save sourced FX rate</button>
          </form>
        </details>
      )}
      {showCosts && (
        <details className="card">
          <summary>Add a cost & quotation coverage</summary>
          <p>
            Separate components already covered by an all-in quote. Blank
            amounts remain unknown. Actual costs are recorded through financial
            review.
          </p>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              const amount = String(f.get("amount"));
              const ids = [String(f.get("evidence"))];
              const line: S["CostLineInput"] = {
                component_key: String(f.get("component")),
                category: String(f.get("category")),
                location: String(f.get("location")),
                payer_party_id: String(f.get("payer")),
                economic_bearer_party_id: String(f.get("bearer")),
                basis: "fixed",
                quantity: null,
                unit: null,
                rate: null,
                minimum_charge: null,
                calculation_rule_ref: null,
                estimate: {
                  low: null,
                  base: amount
                    ? { amount, currency: String(f.get("currency")) }
                    : null,
                  high: null,
                },
                evidence_ids: ids,
                covered_components: String(f.get("coverage"))
                  .split(",")
                  .map((v) => v.trim())
                  .filter(Boolean),
                treatment: f.get(
                  "treatment",
                ) as S["CostLineInput"]["treatment"],
                allocations: [],
                payment_term_ids: f.getAll("obligations").map(String),
                status: "quoted",
                conditional: f.get("conditional") === "on",
                valid_until: String(f.get("valid_until")) || null,
                actual_amount: null,
                unknowns: amount
                  ? []
                  : [
                      {
                        field_path: "/estimate/base",
                        status: "missing",
                        reason:
                          "The amount has not been confirmed in the quotation.",
                      },
                    ],
                cash_treatment: f.get(
                  "timing",
                ) as S["CostLineInput"]["cash_treatment"],
              };
              command(root + "/cost-lines", {
                expected_revision: deal.revision,
                cost_line_id: null,
                line,
              });
            }}
          >
            <Input name="component" label="Unique component name" />
            <Input name="category" label="Cost category" />
            <Input name="location" label="Service location" />
            <Party deal={deal} name="payer" label="Paying party" />
            <Party deal={deal} name="bearer" label="Economic bearer" />
            <Input
              name="amount"
              label="Quoted amount (leave blank if unknown)"
              required={false}
            />
            <Input
              name="currency"
              label="Quotation currency"
              value={deal.reporting_currency}
            />
            <Input
              name="coverage"
              label="Included components, comma-separated"
            />
            <label>
              Economic treatment
              <select name="treatment">
                <option value="expense">Expense</option>
                <option value="recoverable_tax">Recoverable tax</option>
                <option value="reimbursable_advance">
                  Reimbursable advance
                </option>
                <option value="capital_allocation">Capital allocation</option>
              </select>
            </label>
            <label>
              Cash timing
              <select name="timing">
                <option value="unknown">Not yet known</option>
                <option value="scheduled">Follow selected obligations</option>
                <option value="paid_before_snapshot">
                  Paid before the opening balance, with evidence
                </option>
              </select>
            </label>
            <label>
              Payer obligations (select multiple if needed)
              <select
                name="obligations"
                multiple
                size={Math.min(5, Math.max(2, obligations.length))}
              >
                {obligations.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.id} · {row.amount?.currency} {row.amount?.amount}
                  </option>
                ))}
              </select>
            </label>
            <Input
              name="valid_until"
              label="Quotation valid until (optional)"
              type="date"
              required={false}
            />
            <label>
              <input name="conditional" type="checkbox" />
              This cost is conditional
            </label>
            <Sources evidence={evidence} />
            <button disabled={!evidence.length}>Save quoted cost</button>
          </form>
        </details>
      )}
      {finance && (
        <>
          <details className="card">
            <summary>Add a payment obligation</summary>
            <p>
              Recording an obligation does not prove payment. Use reviewed
              evidence and the agreed schedule.
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                const at = String(f.get("due"));
                const obligation: S["ObligationInput"] = {
                  payer_party_id: String(f.get("payer")),
                  payee_party_id: String(f.get("payee")),
                  amount: f.get("amount")
                    ? {
                        amount: String(f.get("amount")),
                        currency: String(f.get("currency")),
                      }
                    : null,
                  schedule: {
                    kind: "fixed",
                    due: {
                      instant: new Date(at + "Z").toISOString(),
                      timezone: "UTC",
                    },
                  },
                  allocations: [],
                  evidence_ids: [String(f.get("evidence"))],
                  unknowns: [],
                  ...(f.get("sequence")
                    ? { sequence: Number(f.get("sequence")) }
                    : {}),
                };
                command(root + "/obligations", {
                  expected_revision: deal.revision,
                  obligation_id: null,
                  obligation,
                });
              }}
            >
              <Party deal={deal} name="payer" label="Obligation payer" />
              <Party deal={deal} name="payee" label="Obligation payee" />
              <Input
                name="amount"
                label="Obligation amount (leave blank if unknown)"
                required={false}
              />
              <Input
                name="currency"
                label="Obligation currency"
                value={deal.reporting_currency}
              />
              <Input name="due" label="Due time (UTC)" type="datetime-local" />
              <Input
                name="sequence"
                label="Same-time sequence, if known"
                type="number"
                required={false}
              />
              <Sources evidence={evidence} />
              <button disabled={!evidence.length}>Save obligation</button>
            </form>
          </details>
          <details className="card">
            <summary>Evidenced settlement adjustments</summary>
            <p>
              A bank-fee deduction reduces the balance and records its expense
              once. A write-off is different from payment. Reimbursement claims
              require a reviewed actual advance.
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                const obligation = obligations.find(
                  (row) => row.id === f.get("obligation"),
                );
                if (!obligation?.amount) return;
                const adjustment: S["SettlementAdjustment"] = {
                  obligation_id: obligation.id,
                  kind,
                  amount: {
                    amount: String(f.get("amount")),
                    currency: obligation.amount.currency,
                  },
                  reason: String(f.get("reason")),
                  agreement_evidence_ids: [String(f.get("agreement"))],
                  ...(kind === "reimbursement"
                    ? { cost_line_id: String(f.get("cost")) }
                    : {}),
                  ...(kind === "settlement"
                    ? {
                        value_date: String(f.get("value_date")),
                        fx_observation_id: String(f.get("fx")) || null,
                        settled_at: f.get("settled_at")
                          ? new Date(
                              String(f.get("settled_at")) + "Z",
                            ).toISOString()
                          : null,
                      }
                    : {}),
                };
                command(root + "/reconcile", {
                  expected_revision: deal.revision,
                  actual_evidence_ids: [String(f.get("evidence"))],
                  adjustments: [adjustment],
                });
              }}
            >
              <label>
                Adjustment type
                <select
                  value={kind}
                  onChange={(e) => setKind(e.target.value as typeof kind)}
                >
                  <option value="fee">Agreed bank-fee deduction</option>
                  <option value="reimbursement">
                    Actual advance reimbursement claim
                  </option>
                  <option value="write_off">
                    Reviewed remaining-balance write-off
                  </option>
                  <option value="settlement">
                    Settlement performed outside the app
                  </option>
                </select>
              </label>
              <label>
                Related obligation
                <select name="obligation" required>
                  {obligations
                    .filter((row) => row.amount)
                    .map((row) => (
                      <option key={row.id} value={row.id}>
                        {row.id} · {row.amount?.currency} {row.amount?.amount}
                      </option>
                    ))}
                </select>
              </label>
              <Input
                name="amount"
                label="Adjustment amount in obligation currency"
              />
              {kind === "reimbursement" && (
                <label>
                  Related actual advance
                  <select name="cost" required>
                    {costs
                      .filter(
                        (row) =>
                          row.treatment === "reimbursable_advance" &&
                          row.actual_amount,
                      )
                      .map((row) => (
                        <option key={row.id} value={row.id}>
                          {row.component_key}
                        </option>
                      ))}
                  </select>
                </label>
              )}
              {kind === "settlement" && (
                <>
                  <Input
                    name="value_date"
                    label="Settlement value date"
                    type="date"
                  />
                  <Input
                    name="settled_at"
                    label="Settlement time (UTC, if known)"
                    type="datetime-local"
                    required={false}
                  />
                </>
              )}
              <Sources
                evidence={evidence}
                name="agreement"
                label="Adjustment agreement evidence"
              />
              <Sources evidence={evidence} label="Supporting actual evidence" />
              <Input name="reason" label="Adjustment reason" />
              <button disabled={!evidence.length}>
                Record adjustment & reconcile
              </button>
            </form>
          </details>
        </>
      )}
    </>
  );
}
