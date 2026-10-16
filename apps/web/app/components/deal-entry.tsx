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
      <summary>Tambahkan persyaratan yang perlu diperiksa</summary>
      <p>
        Masukkan aturan yang bersumber dan alasan keberlakuannya untuk negara,
        barang dan pengiriman ini. Aturan baru belum dinyatakan terpenuhi.
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
        <Input name="country" label="Negara yurisdiksi aturan (ISO)" />
        <label>
          Subjek persyaratan
          <select name="subject">
            <option value="exporter">Eksportir</option>
            <option value="producer">Produsen</option>
            <option value="importer">Importir</option>
            <option value="shipment">Pengiriman</option>
          </select>
        </label>
        <Input name="category" label="Nama persyaratan" />
        <Input name="basis" label="Fakta yang menentukan keberlakuan" />
        <Party deal={deal} name="owner" label="Pihak yang bertanggung jawab" />
        <Input
          name="due"
          type="date"
          label="Tinjau kembali pada tanggal (opsional)"
          required={false}
        />
        <Sources evidence={evidence} />
        <button disabled={!evidence.length}>
          Catat persyaratan untuk ditinjau
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
      <summary>Batas dan preferensi pemilik</summary>
      <p>
        Perbandingan skenario mengikuti batas yang Anda tetapkan. Perubahan
        batas atau saldo memerlukan perhitungan dan tinjauan baru.
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
              "Lengkapi saldo, komitmen, cadangan dan waktu saldo bersama; nilai kosong tidak dianggap nol.",
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
          <legend>Saldo awal dan batas kas</legend>
          <p>
            Saldo ini belum diverifikasi. Perubahan saldo atau waktunya
            membutuhkan tinjauan sumber saldo yang baru. Biarkan seluruh nilai
            kas kosong jika belum diketahui.
          </p>
          <Input
            name="cash"
            label="Saldo tersedia"
            value={cash?.available.amount}
            required={false}
          />
          <Input
            name="committed"
            label="Komitmen di luar transaksi"
            value={cash?.committed_elsewhere.amount}
            required={false}
          />
          <Input
            name="buffer"
            label="Cadangan kas minimum"
            value={cash?.minimum_buffer.amount}
            required={false}
          />
          <Input
            name="cash_currency"
            label="Mata uang saldo"
            value={cash?.available.currency || deal.reporting_currency}
          />
          <Input
            name="committed_currency"
            label="Mata uang komitmen di luar transaksi"
            value={
              cash?.committed_elsewhere.currency || deal.reporting_currency
            }
          />
          <Input
            name="buffer_currency"
            label="Mata uang cadangan minimum"
            value={cash?.minimum_buffer.currency || deal.reporting_currency}
          />
          <Input
            name="cash_at"
            label="Waktu saldo yang diketahui (UTC)"
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
          label="Target margin kontribusi sebagai fraksi 0–1 (opsional)"
          value={constraints.target_contribution_margin || ""}
          required={false}
        />
        <Input
          name="tenor"
          label="Batas tempo kredit dalam hari (opsional)"
          type="number"
          value={constraints.credit_tenor_limit_days?.toString()}
          required={false}
        />
        <Input
          name="deadline"
          type="date"
          label={
            "Batas pengiriman lokal (" + deal.owner_timezone + "), opsional"
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
          Prioritas perbandingan
          <select
            name="ranking"
            defaultValue={constraints.ranking_preference || ""}
          >
            <option value="">Belum dipilih</option>
            <option value="cash">Ketersediaan kas</option>
            <option value="margin">Margin</option>
            <option value="payment_risk">Paparan pembayaran</option>
            <option value="balanced">Seimbang</option>
          </select>
        </label>
        <fieldset>
          <legend>Ketentuan yang boleh diusulkan berubah</legend>
          {[
            [
              "buyer payment terms",
              "Syarat pembayaran pembeli",
              "/payment_terms",
            ],
            [
              "supplier payment terms",
              "Syarat pembayaran pemasok",
              "/payment_terms",
            ],
            [
              deal.business_profile === "producer"
                ? "production inputs"
                : "supplier procurement",
              "Pengadaan atau produksi",
              "/procurement",
            ],
            ["invoice terms", "Nilai invoice", "/invoices"],
            ["shipment terms", "Ketentuan pengiriman", "/shipments"],
            ["goods specifications", "Spesifikasi barang", "/line_items"],
            ["counterparty identities", "Identitas pihak terkait", "/parties"],
            ["funding", "Pilihan pendanaan", "funding"],
            ["owner constraints", "Batas pemilik", "/constraints"],
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
        <Input name="reason" label="Alasan perubahan batas pemilik" />
        <button disabled={!evidence.length}>Simpan batas pemilik</button>
      </form>
    </details>
  );
}
export function PartyEntry({ deal, evidence, command }: Props) {
  return (
    <details className="card">
      <summary>Tambahkan pihak transaksi</summary>
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
                  reason: "Menambahkan pihak dengan bukti identitas",
                  evidence_ids: [source],
                  agreement_required_from: deal.parties.map((p) => p.id),
                },
              ],
            },
            "PATCH",
          );
        }}
      >
        <Input name="name" label="Nama tampilan pihak baru" />
        <Input
          name="legal"
          label="Nama badan hukum (jika diketahui)"
          required={false}
        />
        <Input
          name="registration"
          label="Nomor registrasi (jika diketahui)"
          required={false}
        />
        <Input name="country" label="Negara pihak baru (ISO)" />
        <label>
          Peran pihak baru
          <select name="role">
            <option value="buyer">Pembeli</option>
            <option value="supplier">Pemasok</option>
            <option value="production_input">Pemasok input produksi</option>
            <option value="carrier">Pengangkut</option>
            <option value="forwarder">Forwarder</option>
            <option value="broker">Broker</option>
            <option value="lender">Pemberi dana</option>
            <option value="laboratory">Laboratorium</option>
            <option value="importer">Importir</option>
          </select>
        </label>
        <Sources evidence={evidence} />
        <button disabled={!evidence.length}>Simpan pihak baru</button>
      </form>
    </details>
  );
}
