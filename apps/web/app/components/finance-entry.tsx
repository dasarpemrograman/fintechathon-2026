"use client";
import { useState } from "react";
import { Input, Sources } from "./financial-entry";
import type { components } from "../../../../packages/contracts/api";
type S = components["schemas"];
type Command = (
  path: string,
  body: unknown,
  method?: string,
) => Promise<unknown>;
export function FinanceEntry({
  deal,
  evidence,
  analysis,
  products,
  packs,
  funding,
  command,
  run,
}: {
  deal: S["Deal"];
  evidence: S["Evidence"][];
  analysis?: S["Analysis"];
  products: S["FinanceProduct"][];
  packs: S["FinancePack"][];
  funding: S["FundingOption"][];
  command: Command;
  run: (path: string, body: unknown) => Promise<void>;
}) {
  const [eventRows, setEventRows] = useState(3);
  const root = "deals/" + deal.id;
  return (
    <>
      <details className="card">
        <summary>Record sourced financing product terms</summary>
        <p>
          Record only terms stated by the source. A missing rate still requires
          a quotation. Product fit and document readiness are not lender
          approval.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            const source = String(f.get("evidence")),
              currency = String(f.get("currency"));
            const rate = String(f.get("rate")) || null;
            const fee = String(f.get("fee"));
            const split = (key: string) =>
              String(f.get(key) || "")
                .split("\n")
                .map((v) => v.trim())
                .filter(Boolean);
            const financeProduct: S["FinanceProductInput"] = {
              provider: String(f.get("provider")),
              jurisdiction: String(f.get("country")).toUpperCase(),
              source_ids: [source],
              stage: f.get("stage") as S["FinanceProductInput"]["stage"],
              eligible_entity_types: split("entities"),
              eligible_instruments: [
                f.get("instrument") as NonNullable<
                  S["FinanceProductInput"]["eligible_instruments"]
                >[number],
              ],
              minimum_tenor_days: f.get("min_tenor")
                ? Number(f.get("min_tenor"))
                : null,
              maximum_tenor_days: f.get("max_tenor")
                ? Number(f.get("max_tenor"))
                : null,
              eligibility_predicates: [],
              document_requirements: split("documents").map((name) => ({
                name,
                basis: "provider_required",
                status:
                  f.get("documents_reviewed") === "on"
                    ? "present"
                    : "needs_review",
                evidence_ids: [source],
              })),
              rate,
              rate_basis: rate ? String(f.get("rate_basis")) : null,
              fees: [
                {
                  name: "Published facility fee",
                  amount: fee ? { amount: fee, currency } : null,
                  rate: null,
                  basis: "fixed",
                  withheld_from_draw: f.get("withheld") === "on",
                  unknowns: fee
                    ? []
                    : [
                        {
                          field_path: "/fees",
                          status: "missing",
                          reason: "The facility fee has not been confirmed.",
                        },
                      ],
                },
              ],
              currency,
              minimum_amount: f.get("minimum")
                ? { amount: String(f.get("minimum")), currency }
                : null,
              maximum_amount: f.get("maximum")
                ? { amount: String(f.get("maximum")), currency }
                : null,
              recourse: f.get(
                "recourse",
              ) as S["FinanceProductInput"]["recourse"],
              security_requirements: split("security"),
              indicative_lead_days: f.get("lead")
                ? Number(f.get("lead"))
                : null,
              valid_until: String(f.get("valid_until")) || null,
            };
            command(root + "/finance-products", {
              expected_revision: deal.revision,
              financeProduct,
            });
          }}
        >
          <Input name="provider" label="Financing provider name" />
          <Input
            name="country"
            label="Eligible entity country (ISO)"
            value={deal.seller_domicile || undefined}
          />
          <Input
            name="currency"
            label="Product currency"
            value={deal.reporting_currency}
          />
          <label>
            Funding stage
            <select name="stage">
              <option value="pre_shipment">Pre-shipment</option>
              <option value="post_shipment">Post-shipment</option>
              <option value="working_capital">Working capital</option>
            </select>
          </label>
          <label>
            Supported entity types (one per line)
            <textarea name="entities" />
          </label>
          <label>
            Supported buyer instruments
            <select name="instrument">
              <option value="open_account">Open account</option>
              <option value="lc">Letter of credit</option>
              <option value="milestone">Milestone payments</option>
              <option value="collection">Collection</option>
              <option value="advance">Advance payment</option>
              <option value="other">Other</option>
            </select>
          </label>
          <div className="split">
            <Input
              name="minimum"
              label="Minimum amount (optional)"
              required={false}
            />
            <Input
              name="maximum"
              label="Maximum amount (optional)"
              required={false}
            />
            <Input
              name="min_tenor"
              type="number"
              label="Minimum tenor in days (optional)"
              required={false}
            />
            <Input
              name="max_tenor"
              type="number"
              label="Maximum tenor in days (optional)"
              required={false}
            />
          </div>
          <Input
            name="rate"
            label="Rate as a fraction, e.g. 0.12 (optional)"
            required={false}
          />
          <label>
            Rate basis
            <select name="rate_basis">
              <option value="annual_simple">Annual simple interest</option>
              <option value="monthly_simple">Monthly simple interest</option>
              <option value="flat_total">Fixed total</option>
            </select>
          </label>
          <Input
            name="fee"
            label="Fixed facility fee; enter 0 only if the source confirms it"
            required={false}
          />
          <label>
            <input name="withheld" type="checkbox" />
            Fee withheld at drawdown
          </label>
          <Input
            name="lead"
            type="number"
            label="Estimated processing time in days (optional)"
            required={false}
          />
          <label>
            Recourse
            <select name="recourse">
              <option value="unknown">Not yet known</option>
              <option value="yes">Yes</option>
              <option value="no">None</option>
            </select>
          </label>
          <label>
            Required security (one per line)
            <textarea name="security" />
          </label>
          <label>
            Provider-required documents (one per line)
            <textarea name="documents" />
          </label>
          <label>
            <input type="checkbox" name="documents_reviewed" />
            Selected evidence covers documents already reviewed
          </label>
          <Input
            name="valid_until"
            label="Terms valid until (optional)"
            type="date"
            required={false}
          />
          <Sources evidence={evidence} />
          <button disabled={!evidence.length}>Save product terms</button>
        </form>
      </details>
      {analysis && (
        <details className="card">
          <summary>Check financing product fit</summary>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              const f = new FormData(e.currentTarget);
              const source = String(f.get("evidence"));
              const seller = deal.parties.find((row) =>
                row.roles.includes("seller"),
              );
              if (!seller) return;
              const body: S["FinanceOptionsRequest"] = {
                expected_revision: deal.revision,
                analysis_id: analysis.id,
                company: {
                  seller_party_id: seller.id,
                  entity_type: String(f.get("entity")) || null,
                  registration_evidence_ids: [source],
                  financial_evidence_ids: [String(f.get("financial"))],
                  security_predicates: String(f.get("security") || "")
                    .split("\n")
                    .filter(Boolean)
                    .map((name) => ({
                      name,
                      status: "satisfied",
                      reason: "Security checked against selected evidence",
                      evidence_ids: [source],
                    })),
                  unknowns: [],
                },
                requested_amount: {
                  amount: String(f.get("amount")),
                  currency: String(f.get("currency")),
                },
                required_by: {
                  date: String(f.get("required")),
                  timezone: deal.owner_timezone,
                },
                funding_stage: f.get(
                  "stage",
                ) as S["FinanceOptionsRequest"]["funding_stage"],
                requested_tenor_days: Number(f.get("tenor")),
                invoice_id: String(f.get("invoice")) || null,
              };
              run(root + "/finance-options", body);
            }}
          >
            <Input name="entity" label="Applicant entity type" />
            <Input name="amount" label="Required funding amount" />
            <Input
              name="currency"
              label="Required funding currency"
              value={deal.reporting_currency}
            />
            <Input name="tenor" type="number" label="Requested tenor in days" />
            <Input
              name="required"
              type="date"
              label={
                "Funding needed on local date (" + deal.owner_timezone + ")"
              }
            />
            <label>
              Funding need stage
              <select name="stage">
                <option value="pre_shipment">Pre-shipment</option>
                <option value="post_shipment">Post-shipment</option>
                <option value="working_capital">Working capital</option>
              </select>
            </label>
            <label>
              Invoice to finance
              <select name="invoice">
                <option value="">All related buyer invoices</option>
                {deal.invoices.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.id} · {row.amount.currency} {row.amount.amount}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Evidenced security (one per line)
              <textarea name="security" />
            </label>
            <Sources
              evidence={evidence}
              label="Reviewed registration & security evidence"
            />
            <Sources
              evidence={evidence}
              name="financial"
              label="Reviewed financial statements"
            />
            <button disabled={!evidence.length}>Check recorded products</button>
          </form>
        </details>
      )}
      <details className="card">
        <summary>Record a funding schedule scenario</summary>
        <p>
          This proposal remains hypothetical. Record gross drawdown, withheld
          fees, interest, and repayment separately. Blank amounts are not
          assumed to be zero.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            const f = new FormData(e.currentTarget);
            const currency = String(f.get("currency")),
              source = String(f.get("evidence"));
            const schedule: S["FinancingEvent"][] = Array.from(
              { length: eventRows },
              (_, n) => ({
                kind: f.get("kind" + n) as S["FinancingEvent"]["kind"],
                amount: { amount: String(f.get("amount" + n)), currency },
                schedule: {
                  kind: "fixed",
                  due: {
                    instant: new Date(
                      String(f.get("at" + n)) + "Z",
                    ).toISOString(),
                    timezone: "UTC",
                  },
                },
                status: "proposed",
                evidence_ids: [source],
                ...(f.get("order" + n)
                  ? { sequence: Number(f.get("order" + n)) }
                  : {}),
              }),
            );
            const fundingOption: S["FundingOptionInput"] = {
              product_id: String(f.get("product")) || null,
              fit: "needs_information",
              fit_reasons: [
                "User-proposed schedule; product fit and actual disbursement require separate review.",
              ],
              failed_predicates: [],
              unknown_predicates: ["Not a lender commitment"],
              draw: { amount: String(f.get("draw")), currency },
              earliest_draw_milestone_id: null,
              schedule,
              assumptions: [
                {
                  field_path: "/funding",
                  status: "unreviewed",
                  reason: "User-entered funding schedule scenario",
                },
              ],
              status: "proposed",
              external_facility_evidence_ids: [source],
            };
            command(root + "/funding-options", {
              expected_revision: deal.revision,
              fundingOption,
            });
          }}
        >
          <label>
            Source product (optional)
            <select name="product">
              <option value="">User assumption</option>
              {products.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.provider} · {row.stage}
                </option>
              ))}
            </select>
          </label>
          <Input
            name="currency"
            label="Funding schedule currency"
            value={deal.reporting_currency}
          />
          <Input name="draw" label="Nominal principal drawdown" />
          {Array.from({ length: eventRows }, (_, n) => (
            <fieldset key={n}>
              <legend>Funding events {n + 1}</legend>
              <label>
                Cash movement type
                <select
                  name={"kind" + n}
                  defaultValue={
                    n === 0
                      ? "loan_draw"
                      : n === 1
                        ? "finance_cost"
                        : "principal_repayment"
                  }
                >
                  <option value="loan_draw">Gross drawdown</option>
                  <option value="withheld_fee">
                    Fee withheld from drawdown
                  </option>
                  <option value="interest">Interest</option>
                  <option value="finance_cost">Separately paid fee</option>
                  <option value="principal_repayment">
                    Principal repayment
                  </option>
                </select>
              </label>
              <Input name={"amount" + n} label={"Event amount " + (n + 1)} />
              <Input
                name={"at" + n}
                label={"Event time " + (n + 1) + " (UTC)"}
                type="datetime-local"
              />
              <Input
                name={"order" + n}
                label="Same-time sequence, if known"
                type="number"
                required={false}
              />
            </fieldset>
          ))}
          <button
            type="button"
            className="secondary"
            onClick={() => setEventRows((n) => n + 1)}
          >
            Add funding event
          </button>
          <Sources evidence={evidence} />
          <button disabled={!evidence.length}>
            Save proposed funding schedule
          </button>
        </form>
      </details>
      {analysis &&
        funding.map((option) => (
          <details className="card" key={option.id}>
            <summary>
              Application preparation · {option.draw?.currency}{" "}
              {option.draw?.amount}
            </summary>
            <p>
              Requires a current scenario selecting this facility. The pack is
              not submitted and does not indicate approval or disbursement.
            </p>
            <button
              disabled={!option.product_id}
              onClick={() =>
                run(root + "/finance-packs", {
                  expected_revision: deal.revision,
                  funding_option_id: option.id,
                  scenario_id: analysis.scenario_id,
                  evidence_ids: evidence.map((row) => row.id),
                })
              }
            >
              Prepare a pack from this analysis
            </button>
          </details>
        ))}
      {packs.map((pack) => (
        <details className="card" key={pack.id}>
          <summary>
            Saved pack · {pack.preparation_status || "needs review"}
          </summary>
          <p>
            {pack.requested_amount?.currency} {pack.requested_amount?.amount} ·
            tenor {pack.tenor_days ?? "not yet known"} days
          </p>
          {pack.documents.map((row, n) => (
            <p key={n}>
              {row.name} ·{" "}
              {row.basis === "provider_required"
                ? "Required by provider"
                : "Recommended by analysis"}{" "}
              · {row.status}
            </p>
          ))}
          {pack.gaps.map((row, n) => (
            <p key={n}>{row.reason}</p>
          ))}
          <a
            href={
              "/api/gateway/" +
              root +
              "/artifacts/" +
              pack.artifact.id +
              "/content"
            }
          >
            Download preparation pack draft
          </a>
        </details>
      ))}
    </>
  );
}
