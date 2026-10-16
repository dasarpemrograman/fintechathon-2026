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
      Bukti pendukung yang telah ditinjau
      <select name="evidence" required defaultValue="">
        <option value="" disabled>
          Pilih bukti
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
      Alasan / catatan tinjauan
      <textarea name="reason" required rows={2} />
    </label>
  );
}
function Amount() {
  return (
    <label>
      Jumlah aktual
      <input
        name="amount"
        inputMode="decimal"
        required
        placeholder="Contoh: 1500000.50"
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
      {tab === "Ringkasan" && editor && (
        <Parties deal={deal} evidence={evidence} command={command} />
      )}
      {tab === "Draf & persetujuan" && editor && (
        <section className="card">
          <h2>Penerimaan pihak terkait</h2>
          <p className="muted">
            Catat bukti penerimaan yang dilakukan di luar aplikasi. Tinjauan
            pemilik tidak mewakili pihak lain.
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
              Pihak yang menerima ketentuan saat ini
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
                <input type="checkbox" required style={{ width: "auto" }} />{" "}
                Saya memeriksa bukti penerimaan ketentuan revisi {revision}.
              </span>
            </label>
            <button>Catat penerimaan eksternal</button>
          </form>
        </section>
      )}
      {tab === "Kesiapan & jadwal" && (
        <>
          {editor && (
            <ShipmentEntry deal={deal} evidence={evidence} command={command} />
          )}

          {finance && context.cash_snapshot_hash && (
            <section className="card">
              <h2>Tinjau saldo awal</h2>
              <p className="muted">
                Verifikasi bukti saldo dan komitmen di luar transaksi. Ini tidak
                mencatat pembayaran atau pencairan.
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
                <button>Verifikasi sumber saldo awal</button>
              </form>
            </section>
          )}
          {production && (
            <>
              <section className="card">
                <h2>Tinjau persyaratan</h2>
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
                        Keberlakuan
                        <select
                          name="applicability"
                          defaultValue={r.applicability}
                        >
                          <option value="unresolved">Belum dipastikan</option>
                          <option value="applies">Berlaku</option>
                          <option value="not_applicable">
                            Tidak berlaku, dengan bukti
                          </option>
                        </select>
                      </label>
                      <label>
                        Pemenuhan
                        <select
                          name="fulfillment"
                          defaultValue={r.fulfillment_status}
                        >
                          <option value="missing">Belum ada</option>
                          <option value="submitted">Bukti diajukan</option>
                          <option value="verified">Bukti diverifikasi</option>
                          <option value="rejected">Ditolak</option>
                          <option value="expired">Kedaluwarsa</option>
                        </select>
                      </label>
                      <Source evidence={evidence} />
                      <Reason />
                      <button>Simpan tinjauan persyaratan</button>
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
              <h2>Catat pelaksanaan pengiriman eksternal</h2>
              <p className="muted">
                Catatan ini tidak memesan angkutan atau mengajukan dokumen. Jika
                tindakan dilakukan saat gerbang terblokir, simpan alasan
                pengecualiannya.
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
                  Pengiriman
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
                  Peristiwa
                  <select name="kind">
                    <option value="booking">
                      Pemesanan dilakukan di luar aplikasi
                    </option>
                    <option value="in_transit">Dalam perjalanan</option>
                    <option value="delivered">Diserahkan</option>
                    <option value="exception">Pengecualian</option>
                  </select>
                </label>
                <label>
                  Waktu kejadian (UTC)
                  <input name="occurred_at" type="datetime-local" required />
                </label>
                <Source evidence={evidence} />
                <label>
                  Alasan pengecualian jika gerbang belum terpenuhi
                  <textarea name="exception_reason" />
                </label>
                <button>Catat kejadian eksternal</button>
              </form>
            </section>
          )}
          {(editor || finance || production) && (
            <section className="card">
              <h2>Catat milestone eksternal</h2>
              <p className="muted">
                Jadwal internal tetap tersedia tanpa Calendar. Perubahan
                prakiraan tidak mengubah janji tanggal tetap.
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
                  Peristiwa
                  <select name="kind">
                    <option value="arrival">Perkiraan tiba</option>
                    <option value="acceptance">Penerimaan barang</option>
                    <option value="production_complete">
                      Produksi selesai
                    </option>
                    <option value="delivery">Pengantaran</option>
                  </select>
                </label>
                <label>
                  Jenis tanggal
                  <select name="date_kind">
                    <option value="forecast">Prakiraan</option>
                    <option value="agreed">Disepakati</option>
                    <option value="actual">Aktual dengan bukti</option>
                  </select>
                </label>
                <label>
                  Tanggal lokal ({deal.owner_timezone})
                  <input name="date" type="date" required />
                </label>
                <Source evidence={evidence} />
                <button>Catat milestone</button>
              </form>
            </section>
          )}
        </>
      )}
      {tab === "Biaya & arus kas" && finance && (
        <section className="card">
          <h2>Finalisasi biaya aktual</h2>
          <p className="muted">
            Nilai aktual menggantikan estimasi untuk komponen yang sama.
            Estimasi dan baseline awal tetap tersimpan.
          </p>
          {costs.map((c) => (
            <details key={c.id}>
              <summary>
                {c.component_key} ·{" "}
                {c.actual_amount ? "Aktual tercatat" : "Belum final"}
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
                  Konversi aktual yang ditinjau (wajib untuk mata uang asing)
                  <select name="fx">
                    <option value="">
                      Tidak berlaku untuk mata uang laporan
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
                  Mata uang
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
                <button>Catat biaya aktual</button>
              </form>
            </details>
          ))}
        </section>
      )}
      {tab === "Pembayaran & penutupan" && finance && (
        <section className="card">
          <h2>Verifikasi dan koreksi bukti pembayaran</h2>
          <p className="muted">
            Setiap verifikasi atau pembalikan menambah riwayat. Bukti asli tetap
            dapat ditelusuri.
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
                    ? "Menunggu verifikasi"
                    : "Terverifikasi"}
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
                    Tindakan
                    <select name="disposition">
                      {r.status === "pending" ? (
                        <>
                          <option value="verified">
                            Verifikasi pembayaran
                          </option>
                          <option value="rejected">Tolak bukti</option>
                        </>
                      ) : (
                        <option value="reversed">
                          Balikkan verifikasi, dengan alasan
                        </option>
                      )}
                    </select>
                  </label>
                  <label>
                    Waktu penyelesaian yang diketahui (UTC, opsional)
                    <input name="settled_at" type="datetime-local" />
                  </label>
                  <label>
                    Konversi aktual yang ditinjau (wajib untuk mata uang asing)
                    <select name="fx">
                      <option value="">
                        Tidak berlaku untuk mata uang laporan
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
                  <button>Simpan tinjauan pembayaran</button>
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
      <h2>Inspeksi dan koreksi barang</h2>
      <p className="muted">
        Foto saja tidak menetapkan mutu yang belum diukur. Isi hasil pengukuran
        dan pilih bukti inspeksi.
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
          Hasil tinjauan
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as typeof status)}
          >
            <option value="evidence_review">Perlu bukti lebih lanjut</option>
            <option value="nonconforming">Tidak sesuai, perlu koreksi</option>
            <option value="ready">Sesuai berdasarkan inspeksi</option>
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
                  Hasil pengukuran {a.name === "quantity" ? "jumlah" : a.name} (
                  {a.unit})<input name={line.id + "_" + a.name} required />
                </label>
              ))}
            </div>
          ))}
        <Source evidence={evidence} />
        <Reason />
        <button>Simpan inspeksi barang</button>
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
      <h2>Lengkapi identitas pihak terkait</h2>
      <p className="muted">
        Perubahan identitas atau peran memerlukan analisis dan penerimaan
        ketentuan yang baru.
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
                    reason: "Identitas pihak terkait diperiksa",
                    evidence_ids: [String(f.get("evidence"))],
                    agreement_required_from: parties.map((p) => p.id),
                  },
                ],
              };
              command("deals/" + deal.id + "/facts", body, "PATCH");
            }}
          >
            <label>
              Nama tampilan
              <input name="name" required defaultValue={p.display_name} />
            </label>
            <label>
              Nama badan hukum
              <input name="legal" defaultValue={p.legal_name || ""} />
            </label>
            <label>
              Negara (kode ISO)
              <input name="country" defaultValue={p.country || ""} />
            </label>
            <Source evidence={evidence} />
            <button>Simpan identitas</button>
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
      <summary>Tambahkan pengiriman dan alokasi barang</summary>
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
                reason: "Lingkup pengiriman diperbarui",
                evidence_ids: [String(f.get("evidence"))],
                agreement_required_from: deal.parties.map((p) => p.id),
              },
            ],
          };
          command("deals/" + deal.id + "/facts", body, "PATCH");
        }}
      >
        <label>
          Negara keberangkatan (ISO)
          <input
            name="dispatch"
            required
            defaultValue={deal.seller_domicile || ""}
          />
        </label>
        <label>
          Negara tujuan (ISO)
          <input name="destination" required />
        </label>
        <label>
          Moda
          <select name="mode">
            <option value="sea_lcl">Laut LCL</option>
            <option value="sea_fcl">Laut FCL</option>
            <option value="air">Udara</option>
            <option value="road">Darat</option>
            <option value="rail">Kereta</option>
            <option value="multimodal">Multimoda</option>
          </select>
        </label>
        <label>
          Incoterm (jika diketahui)
          <input name="incoterm" />
        </label>
        <label>
          Tempat yang disebut dalam ketentuan
          <input name="place" />
        </label>
        {deal.line_items.map((l) => (
          <label key={l.id}>
            Jumlah {l.product.description} ({l.unit})
            <input
              name={l.id}
              inputMode="decimal"
              placeholder="Kosongkan jika tidak dialokasikan"
            />
          </label>
        ))}
        <Source evidence={evidence} />
        <button>Tambahkan pengiriman</button>
      </form>
    </details>
  );
}
