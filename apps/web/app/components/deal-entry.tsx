"use client";
import { useState } from "react";
import { Input, Party, Sources } from "./financial-entry";
import type { components } from "../../../../packages/contracts/api";
type S = components["schemas"];
type Command = (
  path: string,
  body: unknown,
  method?: string,
) => Promise<unknown>;
type Props = { deal: S["Deal"]; evidence: S["Evidence"][]; command: Command };
export function RuleEntry({ deal, evidence, command }: Props) {
  return (
    <details className="card">
      <summary>Add a requirement to review</summary>
      <p>
        Record a sourced rule and explain how it applies to this country,
        product, and shipment. A new rule is not automatically fulfilled.
      </p>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          const requirement: S["RequirementInput"] = {
            jurisdiction: String(f.get("country")).toUpperCase(),
            subject: f.get("subject") as S["RequirementInput"]["subject"],
            category: String(f.get("category")),
            applicability: "unresolved",
            predicate_facts: [String(f.get("basis"))],
            evidence_ids: [String(f.get("evidence"))],
            fulfillment_status: "missing",
            owner_party_id: String(f.get("owner")),
            fulfillment_evidence_ids: [],
            reviewer_id: null,
            review_due: String(f.get("due")) || null,
          };
          command("deals/" + deal.id + "/requirements", {
            expected_revision: deal.revision,
            requirement,
          });
        }}
      >
        <Input name="country" label="Rule jurisdiction (ISO country code)" />
        <label>
          Requirement subject
          <select name="subject">
            <option value="exporter">Exporter</option>
            <option value="producer">Producer</option>
            <option value="importer">Importer</option>
            <option value="shipment">Shipment</option>
          </select>
        </label>
        <Input name="category" label="Requirement name" />
        <Input name="basis" label="Facts that determine applicability" />
        <Party deal={deal} name="owner" label="Responsible party" />
        <Input
          name="due"
          type="date"
          label="Review again on (optional)"
          required={false}
        />
        <Sources evidence={evidence} />
        <button disabled={!evidence.length}>
          Record requirement for review
        </button>
      </form>
    </details>
  );
}
export function OwnerEntry({ deal, evidence, command }: Props) {
  const constraints = deal.constraints;
  const [error, setError] = useState("");
  const cash = constraints.cash_snapshot;
  return (
    <details className="card">
      <summary>Owner constraints & preferences</summary>
      <p>
        Scenario comparisons follow your declared constraints. Changes to
        constraints or cash require a new calculation and review.
      </p>
      <form
        key={deal.revision}
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          const cashFields = ["cash", "committed", "buffer", "cash_at"];
          if (
            cashFields.some((key) => f.get(key)) &&
            !cashFields.every((key) => f.get(key))
          ) {
            setError(
              "Complete the balance, commitments, buffer, and balance time together. Blank amounts are not treated as zero.",
            );
            return;
          }
          setError("");
          const currency = String(f.get("cash_currency"));
          const value: S["OwnerConstraints"] = {
            ...constraints,
            cash_snapshot: cashFields.every((key) => f.get(key))
              ? {
                  available: { amount: String(f.get("cash")), currency },
                  committed_elsewhere: {
                    amount: String(f.get("committed")),
                    currency: String(f.get("committed_currency")),
                  },
                  minimum_buffer: {
                    amount: String(f.get("buffer")),
                    currency: String(f.get("buffer_currency")),
                  },
                  as_of: new Date(String(f.get("cash_at")) + "Z").toISOString(),
                }
              : null,
            target_contribution_margin: String(f.get("margin")) || null,
            credit_tenor_limit_days: f.get("tenor")
              ? Number(f.get("tenor"))
              : null,
            delivery_deadline: f.get("deadline")
              ? {
                  date: String(f.get("deadline")),
                  timezone: deal.owner_timezone,
                }
              : null,
            allowable_changes: f.getAll("allowed").map(String),
            ranking_preference: (f.get("ranking") ||
              null) as S["OwnerConstraints"]["ranking_preference"],
          };
          const patch: S["ConstraintsPatch"] = {
            op: "replace",
            path: "/constraints",
            value,
            reason: String(f.get("reason")),
            evidence_ids: [String(f.get("evidence"))],
            agreement_required_from: [],
          };
          command(
            "deals/" + deal.id + "/facts",
            { expected_revision: deal.revision, patches: [patch] },
            "PATCH",
          );
        }}
      >
        <fieldset>
          <legend>Opening balance & cash limits</legend>
          <p>
            This balance is unverified. Changes to its amount or time require a
            new source review. Leave all cash values blank if they are not
            known.
          </p>
          <Input
            name="cash"
            label="Available balance"
            value={cash?.available.amount}
            required={false}
          />
          <Input
            name="committed"
            label="Commitments outside this deal"
            value={cash?.committed_elsewhere.amount}
            required={false}
          />
          <Input
            name="buffer"
            label="Minimum cash buffer"
            value={cash?.minimum_buffer.amount}
            required={false}
          />
          <Input
            name="cash_currency"
            label="Balance currency"
            value={cash?.available.currency || deal.reporting_currency}
          />
          <Input
            name="committed_currency"
            label="External commitment currency"
            value={
              cash?.committed_elsewhere.currency || deal.reporting_currency
            }
          />
          <Input
            name="buffer_currency"
            label="Minimum buffer currency"
            value={cash?.minimum_buffer.currency || deal.reporting_currency}
          />
          <Input
            name="cash_at"
            label="Known balance time (UTC)"
            type="datetime-local"
            value={
              cash ? new Date(cash.as_of).toISOString().replace(/Z$/, "") : ""
            }
            step="any"
            required={false}
          />
        </fieldset>
        {error && <p role="alert">{error}</p>}
        <Input
          name="margin"
          label="Target contribution margin as a fraction, 0–1 (optional)"
          value={constraints.target_contribution_margin || ""}
          required={false}
        />
        <Input
          name="tenor"
          label="Credit tenor limit in days (optional)"
          type="number"
          value={constraints.credit_tenor_limit_days?.toString()}
          required={false}
        />
        <Input
          name="deadline"
          type="date"
          label={
            "Local delivery deadline (" + deal.owner_timezone + "), optional"
          }
          value={
            constraints.delivery_deadline &&
            "date" in constraints.delivery_deadline
              ? constraints.delivery_deadline.date
              : ""
          }
          required={false}
        />
        <label>
          Comparison priority
          <select
            name="ranking"
            defaultValue={constraints.ranking_preference || ""}
          >
            <option value="">Not selected</option>
            <option value="cash">Cash availability</option>
            <option value="margin">Margin</option>
            <option value="payment_risk">Payment exposure</option>
            <option value="balanced">Balanced</option>
          </select>
        </label>
        <fieldset>
          <legend>Terms that may be proposed for change</legend>
          {[
            ["buyer payment terms", "Buyer payment terms", "/payment_terms"],
            [
              "supplier payment terms",
              "Supplier payment terms",
              "/payment_terms",
            ],
            [
              deal.business_profile === "producer"
                ? "production inputs"
                : "supplier procurement",
              "Procurement or production",
              "/procurement",
            ],
            ["invoice terms", "Invoice value", "/invoices"],
            ["shipment terms", "Shipment terms", "/shipments"],
            ["goods specifications", "Goods specifications", "/line_items"],
            ["counterparty identities", "Counterparty identities", "/parties"],
            ["funding", "Funding options", "funding"],
            ["owner constraints", "Owner constraints", "/constraints"],
          ].map(([category, label, path]) => (
            <label key={category}>
              <input
                type="checkbox"
                name="allowed"
                value={category}
                defaultChecked={
                  constraints.allowable_changes.includes(category) ||
                  constraints.allowable_changes.includes(path)
                }
              />
              {label}
            </label>
          ))}
        </fieldset>
        <Sources evidence={evidence} />
        <Input name="reason" label="Reason for changing owner constraints" />
        <button disabled={!evidence.length}>Save owner constraints</button>
      </form>
    </details>
  );
}
export function PartyEntry({ deal, evidence, command }: Props) {
  return (
    <details className="card">
      <summary>Add a transaction party</summary>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          const source = String(f.get("evidence"));
          const party: S["Party"] = {
            id: "party_" + crypto.randomUUID(),
            display_name: String(f.get("name")),
            legal_name: String(f.get("legal")) || null,
            registration_identifier: String(f.get("registration")) || null,
            country: String(f.get("country")).toUpperCase(),
            roles: [f.get("role") as S["Party"]["roles"][number]],
            evidence_ids: [source],
            unknowns: [],
          };
          command(
            "deals/" + deal.id + "/facts",
            {
              expected_revision: deal.revision,
              patches: [
                {
                  op: "replace",
                  path: "/parties",
                  value: [...deal.parties, party],
                  reason: "Add a party supported by identity evidence",
                  evidence_ids: [source],
                  agreement_required_from: deal.parties.map((p) => p.id),
                },
              ],
            },
            "PATCH",
          );
        }}
      >
        <Input name="name" label="New party display name" />
        <Input
          name="legal"
          label="Legal entity name (if known)"
          required={false}
        />
        <Input
          name="registration"
          label="Registration number (if known)"
          required={false}
        />
        <Input name="country" label="New party country (ISO)" />
        <label>
          New party role
          <select name="role">
            <option value="buyer">Buyer</option>
            <option value="supplier">Supplier</option>
            <option value="production_input">Production input supplier</option>
            <option value="carrier">Carrier</option>
            <option value="forwarder">Forwarder</option>
            <option value="broker">Broker</option>
            <option value="lender">Funder</option>
            <option value="laboratory">Laboratory</option>
            <option value="importer">Importer</option>
          </select>
        </label>
        <Sources evidence={evidence} />
        <button disabled={!evidence.length}>Save new party</button>
      </form>
    </details>
  );
}
