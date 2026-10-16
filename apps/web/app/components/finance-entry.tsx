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
        <summary>Catat syarat produk pembiayaan dari sumber</summary>
        <p>
          Hanya syarat yang dinyatakan sumber. Tarif kosong tetap memerlukan
          penawaran. Pemeriksaan kecocokan dan kesiapan dokumen bukan
          persetujuan pemberi dana.
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
                  name: "Biaya fasilitas yang dipublikasikan",
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
                          reason: "Biaya fasilitas belum dikonfirmasi.",
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
          <Input name="provider" label="Nama penyedia pembiayaan" />
          <Input
            name="country"
            label="Negara badan usaha yang memenuhi syarat (ISO)"
            value={deal.seller_domicile || undefined}
          />
          <Input
            name="currency"
            label="Mata uang produk"
            value={deal.reporting_currency}
          />
          <label>
            Tahap pendanaan
            <select name="stage">
              <option value="pre_shipment">Sebelum pengiriman</option>
              <option value="post_shipment">Sesudah pengiriman</option>
              <option value="working_capital">Modal kerja</option>
            </select>
          </label>
          <label>
            Jenis badan usaha yang didukung (satu per baris)
            <textarea name="entities" />
          </label>
          <label>
            Instrumen pembeli yang didukung
            <select name="instrument">
              <option value="open_account">Open account</option>
              <option value="lc">Letter of credit</option>
              <option value="milestone">Pembayaran milestone</option>
              <option value="collection">Collection</option>
              <option value="advance">Di muka</option>
              <option value="other">Lainnya</option>
            </select>
          </label>
          <div className="split">
            <Input
              name="minimum"
              label="Jumlah minimum (opsional)"
              required={false}
            />
            <Input
              name="maximum"
              label="Jumlah maksimum (opsional)"
              required={false}
            />
            <Input
              name="min_tenor"
              type="number"
              label="Tenor minimum hari (opsional)"
              required={false}
            />
            <Input
              name="max_tenor"
              type="number"
              label="Tenor maksimum hari (opsional)"
              required={false}
            />
          </div>
          <Input
            name="rate"
            label="Tarif sebagai fraksi, misalnya 0.12 (opsional)"
            required={false}
          />
          <label>
            Dasar tarif
            <select name="rate_basis">
              <option value="annual_simple">Bunga sederhana per tahun</option>
              <option value="monthly_simple">Bunga sederhana per bulan</option>
              <option value="flat_total">Total tetap</option>
            </select>
          </label>
          <Input
            name="fee"
            label="Biaya fasilitas tetap; isi 0 hanya jika dinyatakan sumber"
            required={false}
          />
          <label>
            <input name="withheld" type="checkbox" />
            Biaya dipotong saat pencairan
          </label>
          <Input
            name="lead"
            type="number"
            label="Perkiraan waktu proses hari (opsional)"
            required={false}
          />
          <label>
            Hak regres
            <select name="recourse">
              <option value="unknown">Belum diketahui</option>
              <option value="yes">Ada</option>
              <option value="no">Tidak ada</option>
            </select>
          </label>
          <label>
            Jaminan yang disyaratkan (satu per baris)
            <textarea name="security" />
          </label>
          <label>
            Dokumen wajib penyedia (satu per baris)
            <textarea name="documents" />
          </label>
          <label>
            <input type="checkbox" name="documents_reviewed" />
            Bukti terpilih mencakup dokumen yang sudah diperiksa
          </label>
          <Input
            name="valid_until"
            label="Syarat berlaku sampai (opsional)"
            type="date"
            required={false}
          />
          <Sources evidence={evidence} />
          <button disabled={!evidence.length}>Simpan syarat produk</button>
        </form>
      </details>
      {analysis && (
        <details className="card">
          <summary>Periksa kecocokan syarat pembiayaan</summary>
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
                      reason: "Jaminan diperiksa terhadap bukti terpilih",
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
            <Input name="entity" label="Jenis badan usaha pemohon" />
            <Input name="amount" label="Jumlah dana yang diperlukan" />
            <Input
              name="currency"
              label="Mata uang dana yang diperlukan"
              value={deal.reporting_currency}
            />
            <Input
              name="tenor"
              type="number"
              label="Tenor yang diminta dalam hari"
            />
            <Input
              name="required"
              type="date"
              label={
                "Dana diperlukan pada tanggal lokal (" +
                deal.owner_timezone +
                ")"
              }
            />
            <label>
              Tahap kebutuhan dana
              <select name="stage">
                <option value="pre_shipment">Sebelum pengiriman</option>
                <option value="post_shipment">Sesudah pengiriman</option>
                <option value="working_capital">Modal kerja</option>
              </select>
            </label>
            <label>
              Invoice yang dibiayai
              <select name="invoice">
                <option value="">Seluruh invoice pembeli terkait</option>
                {deal.invoices.map((row) => (
                  <option key={row.id} value={row.id}>
                    {row.id} · {row.amount.currency} {row.amount.amount}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Jaminan yang sudah dibuktikan (satu per baris)
              <textarea name="security" />
            </label>
            <Sources
              evidence={evidence}
              label="Bukti registrasi dan jaminan yang diperiksa"
            />
            <Sources
              evidence={evidence}
              name="financial"
              label="Laporan keuangan yang diperiksa"
            />
            <button disabled={!evidence.length}>
              Periksa produk yang tercatat
            </button>
          </form>
        </details>
      )}
      <details className="card">
        <summary>Catat skenario jadwal pendanaan</summary>
        <p>
          Usulan ini tetap hipotetis. Catat pencairan bruto, biaya yang
          dipotong, bunga dan pelunasan secara terpisah; jumlah kosong tidak
          diasumsikan nol.
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
                "Jadwal usulan pengguna; kecocokan dan pencairan aktual memerlukan tinjauan terpisah.",
              ],
              failed_predicates: [],
              unknown_predicates: ["Belum merupakan komitmen pemberi dana"],
              draw: { amount: String(f.get("draw")), currency },
              earliest_draw_milestone_id: null,
              schedule,
              assumptions: [
                {
                  field_path: "/funding",
                  status: "unreviewed",
                  reason: "Skenario jadwal yang dimasukkan pengguna",
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
            Produk sumber (opsional)
            <select name="product">
              <option value="">Asumsi pengguna</option>
              {products.map((row) => (
                <option key={row.id} value={row.id}>
                  {row.provider} · {row.stage}
                </option>
              ))}
            </select>
          </label>
          <Input
            name="currency"
            label="Mata uang jadwal pendanaan"
            value={deal.reporting_currency}
          />
          <Input name="draw" label="Pokok pencairan nominal" />
          {Array.from({ length: eventRows }, (_, n) => (
            <fieldset key={n}>
              <legend>Peristiwa pendanaan {n + 1}</legend>
              <label>
                Jenis arus dana
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
                  <option value="loan_draw">Pencairan bruto</option>
                  <option value="withheld_fee">
                    Biaya dipotong dari pencairan
                  </option>
                  <option value="interest">Bunga</option>
                  <option value="finance_cost">Biaya dibayar terpisah</option>
                  <option value="principal_repayment">Pelunasan pokok</option>
                </select>
              </label>
              <Input
                name={"amount" + n}
                label={"Jumlah peristiwa " + (n + 1)}
              />
              <Input
                name={"at" + n}
                label={"Waktu peristiwa " + (n + 1) + " (UTC)"}
                type="datetime-local"
              />
              <Input
                name={"order" + n}
                label="Urutan pada waktu sama jika diketahui"
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
            Tambah peristiwa dana
          </button>
          <Sources evidence={evidence} />
          <button disabled={!evidence.length}>
            Simpan jadwal pendanaan usulan
          </button>
        </form>
      </details>
      {analysis &&
        funding.map((option) => (
          <details className="card" key={option.id}>
            <summary>
              Persiapan aplikasi · {option.draw?.currency} {option.draw?.amount}
            </summary>
            <p>
              Memerlukan skenario aktif yang memilih fasilitas ini. Paket tidak
              dikirim dan tidak menyatakan persetujuan atau pencairan.
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
              Susun paket persiapan dari analisis ini
            </button>
          </details>
        ))}
      {packs.map((pack) => (
        <details className="card" key={pack.id}>
          <summary>
            Paket tersimpan · {pack.preparation_status || "perlu tinjauan"}
          </summary>
          <p>
            {pack.requested_amount?.currency} {pack.requested_amount?.amount} ·
            tenor {pack.tenor_days ?? "belum diketahui"} hari
          </p>
          {pack.documents.map((row, n) => (
            <p key={n}>
              {row.name} ·{" "}
              {row.basis === "provider_required"
                ? "Wajib penyedia"
                : "Disarankan analisis"}{" "}
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
            Unduh draf paket persiapan
          </a>
        </details>
      ))}
    </>
  );
}
