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
  label = "Bukti yang telah ditinjau",
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
          Pilih bukti
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
          Pilih pihak
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
          <summary>Catat kurs dengan bukti sumber</summary>
          <p>
            Satu unit mata uang dasar setara dengan kurs mata uang kutipan.
            Untuk aktual, pilih bukti konversi bank yang benar-benar terjadi;
            kurs referensi tidak membuktikan dana tersedia.
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
            <Input name="base" label="Mata uang dasar kurs" />
            <Input
              name="quote"
              label="Mata uang kutipan kurs"
              value={deal.reporting_currency}
            />
            <Input name="rate" label="Kurs per satu unit mata uang dasar" />
            <Input
              name="at"
              type="datetime-local"
              label="Waktu kurs yang diketahui (UTC)"
            />
            <Sources evidence={evidence} />
            <button disabled={!evidence.length}>Simpan kurs bersumber</button>
          </form>
        </details>
      )}
      {showCosts && (
        <details className="card">
          <summary>Tambahkan biaya dan cakupan penawaran</summary>
          <p>
            Pisahkan komponen yang sudah termasuk penawaran menyeluruh. Jumlah
            kosong tetap belum diketahui. Biaya aktual dicatat melalui tinjauan
            keuangan.
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
                        reason: "Jumlah belum dikonfirmasi dalam penawaran.",
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
            <Input name="component" label="Nama komponen unik" />
            <Input name="category" label="Kategori biaya" />
            <Input name="location" label="Lokasi layanan" />
            <Party deal={deal} name="payer" label="Pihak yang membayar" />
            <Party
              deal={deal}
              name="bearer"
              label="Pihak yang menanggung secara ekonomi"
            />
            <Input
              name="amount"
              label="Jumlah penawaran (kosong jika belum diketahui)"
              required={false}
            />
            <Input
              name="currency"
              label="Mata uang penawaran"
              value={deal.reporting_currency}
            />
            <Input
              name="coverage"
              label="Komponen yang sudah termasuk, dipisahkan koma"
            />
            <label>
              Perlakuan ekonomi
              <select name="treatment">
                <option value="expense">Beban</option>
                <option value="recoverable_tax">
                  Pajak yang dapat dipulihkan
                </option>
                <option value="reimbursable_advance">
                  Talangan yang ditagihkan kembali
                </option>
                <option value="capital_allocation">Alokasi modal</option>
              </select>
            </label>
            <label>
              Waktu kas
              <select name="timing">
                <option value="unknown">Belum diketahui</option>
                <option value="scheduled">Mengikuti kewajiban terpilih</option>
                <option value="paid_before_snapshot">
                  Sudah dibayar sebelum saldo awal, dengan bukti
                </option>
              </select>
            </label>
            <label>
              Kewajiban pembayar (dapat memilih beberapa)
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
              label="Penawaran berlaku sampai (opsional)"
              type="date"
              required={false}
            />
            <label>
              <input name="conditional" type="checkbox" />
              Biaya masih bersyarat
            </label>
            <Sources evidence={evidence} />
            <button disabled={!evidence.length}>Simpan biaya penawaran</button>
          </form>
        </details>
      )}
      {finance && (
        <>
          <details className="card">
            <summary>Tambahkan kewajiban pembayaran</summary>
            <p>
              Catatan kewajiban belum membuktikan pembayaran. Gunakan bukti dan
              jadwal yang disepakati.
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
              <Party deal={deal} name="payer" label="Pembayar kewajiban" />
              <Party deal={deal} name="payee" label="Penerima kewajiban" />
              <Input
                name="amount"
                label="Jumlah kewajiban (kosong jika belum diketahui)"
                required={false}
              />
              <Input
                name="currency"
                label="Mata uang kewajiban"
                value={deal.reporting_currency}
              />
              <Input
                name="due"
                label="Waktu jatuh tempo (UTC)"
                type="datetime-local"
              />
              <Input
                name="sequence"
                label="Urutan pada waktu yang sama, jika diketahui"
                type="number"
                required={false}
              />
              <Sources evidence={evidence} />
              <button disabled={!evidence.length}>Simpan kewajiban</button>
            </form>
          </details>
          <details className="card">
            <summary>Penyesuaian penyelesaian dengan bukti</summary>
            <p>
              Potongan biaya bank mengurangi saldo dan mencatat beban sekali.
              Hapus buku berbeda dari lunas. Klaim penggantian talangan
              memerlukan biaya aktual yang sudah ditinjau.
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
                Jenis penyesuaian
                <select
                  value={kind}
                  onChange={(e) => setKind(e.target.value as typeof kind)}
                >
                  <option value="fee">
                    Potongan biaya bank yang disepakati
                  </option>
                  <option value="reimbursement">
                    Klaim penggantian talangan aktual
                  </option>
                  <option value="write_off">
                    Hapus buku sisa saldo, dengan tinjauan
                  </option>
                  <option value="settlement">
                    Penyelesaian yang sudah dilakukan di luar aplikasi
                  </option>
                </select>
              </label>
              <label>
                Kewajiban terkait
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
                label="Jumlah penyesuaian dalam mata uang kewajiban"
              />
              {kind === "reimbursement" && (
                <label>
                  Talangan aktual terkait
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
                    label="Tanggal nilai penyelesaian"
                    type="date"
                  />
                  <Input
                    name="settled_at"
                    label="Waktu penyelesaian (UTC, jika diketahui)"
                    type="datetime-local"
                    required={false}
                  />
                </>
              )}
              <Sources
                evidence={evidence}
                name="agreement"
                label="Bukti kesepakatan penyesuaian"
              />
              <Sources evidence={evidence} label="Bukti aktual pendukung" />
              <Input name="reason" label="Alasan penyesuaian" />
              <button disabled={!evidence.length}>
                Catat penyesuaian dan rekonsiliasi
              </button>
            </form>
          </details>
        </>
      )}
    </>
  );
}
