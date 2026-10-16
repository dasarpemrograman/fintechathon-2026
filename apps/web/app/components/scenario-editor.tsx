"use client";
import type { components } from "../../../../packages/contracts/api";
type S = components["schemas"];
const fixedInstant = (schedule: S["Schedule"]) =>
  schedule.kind === "fixed" && "instant" in schedule.due
    ? schedule.due.instant
    : "";
type Command = (
  path: string,
  body: unknown,
  method?: string,
) => Promise<unknown>;
export function ScenarioEditor({
  deal,
  funding,
  disabled,
  command,
  run,
}: {
  deal: S["Deal"];
  funding: S["FundingOption"][];
  disabled: boolean;
  command: Command;
  run: (path: string, body: unknown) => Promise<void>;
}) {
  const root = "deals/" + deal.id;
  return (
    <details className="card">
      <summary>Negosiasikan ketentuan pembeli, pemasok dan produksi</summary>
      <p>
        Ubah beberapa ketentuan bersama dalam satu skenario. Jumlah cicilan
        harus tetap sesuai faktur; kalkulasi dilakukan server. Membandingkan
        usulan tidak mencatat penerimaan pihak lain.
      </p>
      <form
        onSubmit={async (event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          const patches: S["FactPatch"][] = [];
          const changed = (a: unknown, b: unknown) =>
            JSON.stringify(a) !== JSON.stringify(b);
          const required = deal.parties
            .filter((p) => !p.roles.includes("seller"))
            .map((p) => p.id);
          const terms = deal.payment_terms.map((term) => {
            const next = structuredClone(term);
            const amount = String(form.get("amount:" + term.id) || "");
            if (amount && amount !== term.amount?.amount) {
              next.amount = {
                amount,
                currency:
                  term.amount?.currency ||
                  deal.invoices.find((i) => i.id === term.invoice_id)?.amount
                    .currency ||
                  deal.reporting_currency,
              };
              next.invoice_fraction = null;
            }
            const instant = String(form.get("date:" + term.id) || "");
            if (
              instant &&
              (term.schedule.kind !== "fixed" ||
                instant !== fixedInstant(term.schedule))
            )
              next.schedule = {
                kind: "fixed",
                due: { instant, timezone: deal.owner_timezone },
              };
            return next;
          });
          if (changed(terms, deal.payment_terms))
            patches.push({
              op: "replace",
              path: "/payment_terms",
              value: terms,
              reason: "Usulan ketentuan pembayaran gabungan untuk ditinjau.",
              evidence_ids: [],
              agreement_required_from: required,
            });
          const procurement = structuredClone(deal.procurement);
          if (procurement.business_profile === "reseller")
            for (const line of procurement.purchase_lines) {
              const amount = String(
                form.get("input:" + line.line_item_id) || "",
              );
              if (amount)
                line.unit_cost = {
                  amount,
                  currency: line.unit_cost?.currency || deal.reporting_currency,
                };
            }
          else {
            for (const line of procurement.inputs) {
              const amount = String(form.get("input:" + line.id) || "");
              if (amount)
                line.unit_cost = {
                  amount,
                  currency: line.unit_cost?.currency || deal.reporting_currency,
                };
            }
            for (const [index, line] of procurement.costs.entries()) {
              const amount = String(form.get("production:" + index) || "");
              if (amount)
                line.amount = {
                  amount,
                  currency: line.amount?.currency || deal.reporting_currency,
                };
            }
            for (const key of [
              "batch_quantity",
              "capacity_quantity",
              "usable_yield",
            ] as const) {
              const value = String(form.get(key) || "");
              if (value) procurement[key] = value;
            }
          }
          if (changed(procurement, deal.procurement))
            patches.push({
              op: "replace",
              path: "/procurement",
              value: procurement,
              reason:
                "Usulan biaya dan kapasitas pengadaan/produksi untuk ditinjau.",
              evidence_ids: [],
              agreement_required_from: required,
            });
          const apply =
            (event.nativeEvent as SubmitEvent).submitter?.getAttribute(
              "value",
            ) === "apply";
          if (apply) {
            if (patches.length)
              await command(
                root + "/facts",
                { expected_revision: deal.revision, patches },
                "PATCH",
              );
          } else
            await run(root + "/scenarios", {
              expected_revision: deal.revision,
              base_revision: { id: deal.id, revision: deal.revision },
              patches,
              funding_option_ids: form.getAll("funding").map(String),
            });
        }}
      >
        <fieldset disabled={disabled}>
          <legend>Cicilan dan tanggal yang dinegosiasikan</legend>
          {deal.payment_terms.map((term) => (
            <div className="split" key={term.id}>
              <label>
                {term.side === "buyer" ? "Pembeli" : "Pemasok / penyedia"} ·{" "}
                {term.id} · {term.amount?.currency || deal.reporting_currency}
                <input
                  name={"amount:" + term.id}
                  defaultValue={term.amount?.amount || ""}
                  inputMode="decimal"
                  aria-label={"Jumlah cicilan " + term.id}
                />
              </label>
              <label>
                Waktu pembayaran dengan offset zona
                <input
                  name={"date:" + term.id}
                  defaultValue={
                    term.schedule.kind === "fixed"
                      ? fixedInstant(term.schedule)
                      : ""
                  }
                  placeholder="2026-11-01T12:00:00+07:00"
                  aria-label={"Waktu pembayaran " + term.id}
                />
              </label>
            </div>
          ))}
        </fieldset>
        <fieldset disabled={disabled}>
          <legend>
            {deal.business_profile === "producer"
              ? "Input dan biaya produksi"
              : "Harga satuan pengadaan"}
          </legend>
          {deal.procurement.business_profile === "reseller" ? (
            deal.procurement.purchase_lines.map((line) => (
              <label key={line.line_item_id}>
                {line.line_item_id} ·{" "}
                {line.unit_cost?.currency || deal.reporting_currency}
                <input
                  name={"input:" + line.line_item_id}
                  defaultValue={line.unit_cost?.amount || ""}
                  inputMode="decimal"
                />
              </label>
            ))
          ) : (
            <>
              {deal.procurement.inputs.map((line) => (
                <label key={line.id}>
                  {line.description} ·{" "}
                  {line.unit_cost?.currency || deal.reporting_currency} /{" "}
                  {line.unit}
                  <input
                    name={"input:" + line.id}
                    defaultValue={line.unit_cost?.amount || ""}
                    inputMode="decimal"
                  />
                </label>
              ))}
              {deal.procurement.costs.map((line, index) => (
                <label key={index}>
                  {line.category} ·{" "}
                  {line.amount?.currency || deal.reporting_currency}
                  <input
                    name={"production:" + index}
                    defaultValue={line.amount?.amount || ""}
                    inputMode="decimal"
                  />
                </label>
              ))}
              <div className="split">
                <label>
                  Jumlah batch
                  <input
                    name="batch_quantity"
                    defaultValue={deal.procurement.batch_quantity || ""}
                  />
                </label>
                <label>
                  Kapasitas tersedia
                  <input
                    name="capacity_quantity"
                    defaultValue={deal.procurement.capacity_quantity || ""}
                  />
                </label>
                <label>
                  Hasil layak pakai (fraksi, 0.9 = 90%)
                  <input
                    name="usable_yield"
                    defaultValue={deal.procurement.usable_yield || ""}
                  />
                </label>
              </div>
            </>
          )}
        </fieldset>
        <fieldset disabled={disabled}>
          <legend>Opsi pendanaan untuk dibandingkan</legend>
          {funding.map((option) => (
            <label key={option.id}>
              <input type="checkbox" name="funding" value={option.id} />
              {option.id} · {option.fit} · {option.draw?.currency}{" "}
              {option.draw?.amount}
            </label>
          ))}
        </fieldset>
        <div className="actions">
          <button disabled={disabled}>Bandingkan seluruh usulan bersama</button>
          <button
            disabled={disabled}
            className="secondary"
            type="submit"
            value="apply"
          >
            Simpan sebagai fakta usulan transaksi
          </button>
        </div>
      </form>
    </details>
  );
}
