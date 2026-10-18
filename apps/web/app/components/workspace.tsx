"use client";
import { useEffect, useState, type FormEvent } from "react";
import { DiscoveryPanel } from "./discovery-panel";
import { ScenarioEditor } from "./scenario-editor";
import { FinancialEntry } from "./financial-entry";
import { FinanceEntry } from "./finance-entry";
import { RuleEntry, OwnerEntry, PartyEntry } from "./deal-entry";
import { CalendarPanel } from "./calendar-panel";
import { SourceEntry } from "./source-entry";
import { ReviewControls } from "./review-controls";
import type { components } from "../../../../packages/contracts/api";
type S = components["schemas"];
type W = S["Workspace"];
type D = S["Deal"];
type A = S["Analysis"];
async function api<T>(
  path: string,
  body?: unknown,
  method = "POST",
): Promise<T> {
  const response = await fetch("/api/gateway/" + path, {
    method: body === undefined ? "GET" : method,
    headers:
      body instanceof FormData ? {} : { "Content-Type": "application/json" },
    body:
      body === undefined
        ? undefined
        : body instanceof FormData
          ? body
          : JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(
      data.message || data.reason || data.code || "Permintaan gagal.",
    ) as Error & { status: number };
    error.status = response.status;
    throw error;
  }
  return data.result as T;
}
const formatDate = (s: string, timezone = "Asia/Jakarta") =>
  new Intl.DateTimeFormat("id-ID", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: timezone,
  }).format(new Date(s));
const money = (m: S["Money"] | S["SignedMoney"] | null | undefined) =>
  m ? m.currency + " " + m.amount : "Belum diketahui";
const labels: Record<string, string> = {
  analysis: "Analisis",
  commercial_terms: "Kesepakatan",
  funding_preparation: "Persiapan dana",
  execution_gate: "Gerbang tindakan",
  goods: "Barang",
  shipment: "Pengiriman",
  buyer_payment: "Pembayaran pembeli",
  internal_closure: "Penutupan",
  not_started: "Belum dimulai",
  not_booked: "Belum dipesan",
  booking_review: "Tinjauan pemesanan",
  booked: "Pemesanan tercatat",
  in_transit: "Dalam perjalanan",
  delivered: "Diterima",
  exception: "Pengecualian",
  not_due: "Belum jatuh tempo",
  due: "Belum lunas",
  verification_pending: "Menunggu verifikasi",
  partially_paid: "Dibayar sebagian",
  overdue: "Lewat jatuh tempo",
  disputed: "Disengketakan",
  open: "Terbuka",
  not_needed: "Tidak diperlukan",
  needed: "Diperlukan",
  preparing: "Disiapkan",
  comparing: "Dibandingkan",
  application_ready: "Paket persiapan siap ditinjau",
  agreed: "Diterima pihak terkait",
  owner_reviewed: "Ditinjau pemilik",
  awaiting_counterparties: "Menunggu penerimaan pihak",
  superseded: "Digantikan",
  draft: "Draf",
  scoped_complete: "Lengkap untuk cakupan ini",
  expense: "Beban",
  user_assumed: "Asumsi pengguna",
  quoted: "Penawaran",
  published_tariff: "Tarif terbit",
  modeled: "Perkiraan",
  unknown: "Belum diketahui",
  recoverable_tax: "Pajak dapat dipulihkan",
  reimbursable_advance: "Talangan",
  capital_allocation: "Alokasi modal",
  synthetic_demo: "Demo sintetis",
  cached: "Tembolok",
  user_provided: "Diberikan pengguna",
  live: "Sumber langsung",
  loan_draw: "Pencairan pinjaman",
  principal_repayment: "Pelunasan pokok",
  finance_cost: "Biaya pendanaan",
  withheld_fee: "Biaya dipotong",
  interest: "Bunga",
  reserve_release: "Pelepasan cadangan",
  packaging: "Kemasan",
  administration: "Administrasi",
  origin_trucking: "Angkutan asal",
  main_freight: "Angkutan utama",
  destination_delivery: "Pengantaran tujuan",
  production: "Produksi",
  procurement: "Pengadaan",
  materials: "Bahan",
  labor: "Tenaga kerja",
  process: "Proses produksi",
  overhead: "Alokasi overhead",
  analyzed_complete: "Analisis tersedia",
  analyzed_partial: "Analisis parsial",
  needs_input: "Perlu data",
  not_analyzed: "Belum dianalisis",
  owner: "Pemilik",
  export_admin: "Admin ekspor",
  finance_reviewer: "Peninjau keuangan",
  production_procurement: "Produksi dan pengadaan",
  paid: "Lunas pembeli",
  resolved_with_writeoff: "Diselesaikan dengan hapus buku",
  reconciling: "Rekonsiliasi internal",
  closed: "Ditutup",
  blocked: "Terblokir",
  ready_for_next_action: "Siap untuk tahap berikut",
  proposed: "Usulan",
  pending: "Menunggu verifikasi",
  verified: "Terverifikasi",
  succeeded: "Selesai",
  failed: "Gagal",
  partial: "Parsial",
  cancelled: "Dibatalkan",
  queued: "Menunggu",
  running: "Berjalan",
};
const title = (s: string) => labels[s] || s.replaceAll("_", " ");
function componentTitle(key: string, deal: D | null) {
  if (key.startsWith("procurement:")) {
    const line = deal?.line_items.find(
      (row) => row.id === key.slice("procurement:".length),
    );
    return "Pengadaan" + (line ? " · " + line.product.description : " barang");
  }
  if (key.startsWith("production-input:")) {
    const plan = deal?.procurement;
    const input =
      plan?.business_profile === "producer"
        ? plan.inputs.find(
            (row) => row.id === key.slice("production-input:".length),
          )
        : null;
    return "Input produksi" + (input ? " · " + input.description : "");
  }
  if (key.startsWith("production-"))
    return title(key.split(":")[0].slice("production-".length));
  return title(key);
}
function Issues({ items }: { items: S["Issue"][] }) {
  return (
    <>
      {items.map((i, n) => (
        <div className="notice" key={n}>
          <strong>{i.code}</strong>
          <br />
          {i.reason}
          {i.required_action && <p>{i.required_action}</p>}
        </div>
      ))}
    </>
  );
}
function Field({
  name,
  label,
  required = true,
  type = "text",
  value,
}: {
  name: string;
  label: string;
  required?: boolean;
  type?: string;
  value?: string;
}) {
  return (
    <label>
      {label}
      <input name={name} type={type} required={required} defaultValue={value} />
    </label>
  );
}
export default function Workspace() {
  const [session, setSession] = useState<S["Session"] | null>(null),
    [loading, setLoading] = useState(true),
    [error, setError] = useState(""),
    [identities, setIdentities] = useState<
      S["DemoIdentitiesResponse"]["result"]["users"]
    >([]),
    [workspaces, setWorkspaces] = useState<W[]>([]),
    [selected, setSelected] = useState<W | null>(null),
    [creating, setCreating] = useState(false),
    [workspaceCursor, setWorkspaceCursor] = useState<string | null>(null);
  async function load(append = false) {
    const page = await api<S["WorkspacePage"]>(
      "workspaces?limit=25" +
        (append && workspaceCursor
          ? "&cursor=" + encodeURIComponent(workspaceCursor)
          : ""),
    );
    setWorkspaces((old) => (append ? [...old, ...page.items] : page.items));
    setWorkspaceCursor(page.next_cursor);
  }
  useEffect(() => {
    api<S["Session"]>("auth/session")
      .then((s) => {
        setSession(s);
        return load();
      })
      .catch(() =>
        api<S["DemoIdentitiesResponse"]["result"]>("auth/demo-identities")
          .then((d) => setIdentities(d.users))
          .catch(() => {}),
      )
      .finally(() => setLoading(false));
  }, []);
  async function login(body: unknown) {
    setError("");
    try {
      const r = await fetch("/api/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d.message || d.code || "Tidak dapat masuk");
      setSession(d.session);
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function logout() {
    await fetch("/api/session", { method: "DELETE" });
    setSession(null);
    setSelected(null);
  }
  const member = session?.memberships.find(
    (m) => m.organization_id === session.organization_id,
  );
  if (loading) return <main className="loading">Memuat ruang ekspor…</main>;
  return (
    <>
      <header>
        <div className="brand">
          fin<span>cathon</span> <small> / ruang ekspor</small>
        </div>
        {session && (
          <div className="actions">
            <small>
              {session.user.display_name} · {member?.organization_name}
              <br />
              {member?.roles.map(title).join(" / ")}
            </small>
            <label>
              Organisasi
              <select
                value={session.organization_id || ""}
                onChange={async (e) => {
                  try {
                    const updated = await api<S["Session"]>(
                      "auth/organization",
                      { organization_id: e.target.value },
                    );
                    setSession(updated);
                    setSelected(null);
                    await load();
                  } catch (error) {
                    setError((error as Error).message);
                  }
                }}
              >
                <option value="" disabled>
                  Pilih organisasi
                </option>
                {session.memberships.map((m) => (
                  <option key={m.id} value={m.organization_id}>
                    {m.organization_name}
                  </option>
                ))}
              </select>
            </label>
            <button className="secondary" onClick={logout}>
              Keluar
            </button>
          </div>
        )}
      </header>
      <main>
        {!session ? (
          <div className="login">
            <div className="eyebrow">Dari bukti ke keputusan</div>
            <h1>Rencanakan ekspor dengan lebih jelas.</h1>
            <p className="muted">
              Telusuri biaya, arus kas, persetujuan, dan kesiapan transaksi
              dalam satu ruang kerja.
            </p>
            {error && (
              <div role="alert" className="notice error">
                {error}
              </div>
            )}
            <form
              className="card"
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                login({ email: f.get("email"), password: f.get("password") });
              }}
            >
              <h2>Masuk ke organisasi</h2>
              <Field name="email" label="Email" type="email" />
              <Field name="password" label="Kata sandi" type="password" />
              <button>Masuk</button>
            </form>
            {identities.length > 0 && (
              <section className="card">
                <h2>Coba demo offline</h2>
                <p className="muted">
                  Data sintetis. Sumber, pembiayaan, dan hasil bukan penawaran
                  atau bukti transaksi nyata.
                </p>
                <label>
                  Identitas demo
                  <select id="identity">
                    {identities.map((i) => (
                      <option key={i.id} value={i.id}>
                        {i.display_name} · {i.email}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  style={{ marginTop: 14 }}
                  onClick={() =>
                    login({
                      user_id: (
                        document.getElementById("identity") as HTMLSelectElement
                      ).value,
                    })
                  }
                >
                  Masuk demo
                </button>
              </section>
            )}
          </div>
        ) : selected ? (
          <Detail
            workspace={selected}
            session={session}
            onBack={() => {
              setSelected(null);
              load();
            }}
            onWorkspace={setSelected}
          />
        ) : (
          <>
            <div className="row">
              <div>
                <div className="eyebrow">Portofolio ekspor</div>
                <h1>Ruang kerja Anda</h1>
                <p className="muted">
                  Mulai dari eksplorasi, lanjutkan dengan fakta dan bukti yang
                  ditinjau.
                </p>
              </div>
              <button onClick={() => setCreating(!creating)}>
                + Ruang kerja baru
              </button>
            </div>
            {creating && (
              <Create
                onCreate={(w) => {
                  setCreating(false);
                  setSelected(w);
                  load();
                }}
              />
            )}
            <div className="grid">
              {workspaces.map((w) => (
                <article className="card" key={w.id}>
                  <div className="row">
                    <span
                      className={
                        "tag " + (w.execution_scope === "demo" ? "demo" : "")
                      }
                    >
                      {w.execution_scope === "demo"
                        ? "DEMO SINTETIS"
                        : "DATA ORGANISASI"}
                    </span>
                    <span className="tag">
                      {w.mode === "sandbox" ? "Eksplorasi" : "Transaksi"}
                    </span>
                  </div>
                  <h2 style={{ marginTop: 22 }}>{w.product.description}</h2>
                  <p className="muted">
                    {w.seller_domicile || "?"} → {w.destination_country || "?"}{" "}
                    ·{" "}
                    {w.business_profile === "producer"
                      ? "Produsen"
                      : "Reseller"}
                  </p>
                  <div className="row">
                    <small className="muted">
                      {w.reporting_currency} · revisi {w.revision}
                    </small>
                    <button className="link" onClick={() => setSelected(w)}>
                      Buka ruang kerja →
                    </button>
                  </div>
                </article>
              ))}
            </div>
            {workspaces.length === 0 && (
              <p className="empty">
                Belum ada ruang kerja. Mulai dengan produk dan tujuan ekspor.
              </p>
            )}
            {workspaceCursor && (
              <button
                className="secondary"
                onClick={() =>
                  load(true).catch((error) => setError(error.message))
                }
              >
                Muat ruang kerja berikutnya
              </button>
            )}
            <Settings />
            {session && member?.roles.includes("owner") && (
              <MemberAdmin
                session={session}
                onChanged={async () => {
                  const updated = await api<S["Session"]>("auth/session");
                  setSession(updated);
                  if (updated.organization_id) await load();
                  else setWorkspaces([]);
                }}
              />
            )}
          </>
        )}
        <p className="foot">
          Fincathon · Waktu mengikuti zona ruang kerja. Tanggal lokal pada bukti
          tetap dipertahankan.
          <br />
          Persiapan dan pencatatan saja. Tidak ada pengiriman pesan, pembayaran,
          pemesanan, atau pengajuan pembiayaan.
        </p>
      </main>
    </>
  );
}
function Create({ onCreate }: { onCreate: (w: W) => void }) {
  const [error, setError] = useState("");
  return (
    <form
      className="card"
      onSubmit={async (e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        try {
          const body: S["CreateWorkspaceRequest"] = {
            mode: f.get("mode") as W["mode"],
            business_profile: f.get("profile") as W["business_profile"],
            seller_domicile: String(f.get("origin")).toUpperCase() || null,
            dispatch_country: String(f.get("dispatch")).toUpperCase() || null,
            destination_country:
              String(f.get("destination")).toUpperCase() || null,
            reporting_currency: String(f.get("currency")).toUpperCase(),
            owner_timezone: String(f.get("timezone")),
            product: { description: String(f.get("description")) },
          };
          onCreate(await api<W>("workspaces", body));
        } catch (e) {
          setError((e as Error).message);
        }
      }}
    >
      <h2>Mulai dari produk Anda</h2>
      <div className="grid">
        <Field name="description" label="Produk dan bentuk barang" />
        <label>
          Profil usaha
          <select name="profile">
            <option value="reseller">Reseller</option>
            <option value="producer">Produsen</option>
          </select>
        </label>
        <label>
          Mode
          <select name="mode">
            <option value="sandbox">Eksplorasi / sandbox</option>
            <option value="deal">Transaksi</option>
          </select>
        </label>
        <Field
          name="origin"
          label="Domisili penjual (kode ISO, contoh ID)"
          required={false}
        />
        <Field
          name="destination"
          label="Negara tujuan (contoh SG)"
          required={false}
        />
        <Field
          name="dispatch"
          label="Negara keberangkatan barang (ISO, jika diketahui)"
          required={false}
        />
        <Field name="currency" label="Mata uang laporan" value="IDR" />
        <Field
          name="timezone"
          label="Zona waktu pemilik (IANA)"
          value="Asia/Jakarta"
        />
      </div>
      {error && <div role="alert">{error}</div>}
      <button>Buat ruang kerja</button>
    </form>
  );
}
function Detail({
  workspace,
  session,
  onBack,
  onWorkspace,
}: {
  workspace: W;
  session: S["Session"];
  onBack: () => void;
  onWorkspace: (w: W) => void;
}) {
  const [w, setW] = useState(workspace),
    [loaded, setLoaded] = useState(false),
    [deal, setDeal] = useState<D | null>(null),
    [tab, setTab] = useState("Ringkasan"),
    [draftKind, setDraftKind] = useState<S["ArtifactKind"]>("agreement"),
    [draftLanguage, setDraftLanguage] = useState("id"),
    [draftRecipient, setDraftRecipient] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState(""),
    [analyses, setAnalyses] = useState<A[]>([]),
    [evidence, setEvidence] = useState<S["Evidence"][]>([]),
    [docs, setDocs] = useState<S["Document"][]>([]),
    [facts, setFacts] = useState<S["FactCandidate"][]>([]),
    [fx, setFx] = useState<S["FxObservation"][]>([]),
    [costs, setCosts] = useState<S["CostLine"][]>([]),
    [requirements, setRequirements] = useState<S["Requirement"][]>([]),
    [artifacts, setArtifacts] = useState<S["Artifact"][]>([]),
    [financeProducts, setFinanceProducts] = useState<S["FinanceProduct"][]>([]),
    [financePacks, setFinancePacks] = useState<S["FinancePack"][]>([]),
    [funding, setFunding] = useState<S["FundingOption"][]>([]),
    [obligations, setObligations] = useState<S["Obligation"][]>([]),
    [receipts, setReceipts] = useState<S["Receipt"][]>([]),
    [milestones, setMilestones] = useState<S["Milestone"][]>([]),
    [gate, setGate] = useState<S["Gate"] | null>(null),
    [job, setJob] = useState<S["Run"] | null>(null),
    [lastRun, setLastRun] = useState<{
      path: string;
      body: Record<string, unknown>;
    } | null>(null),
    [audit, setAudit] = useState<S["AuditRecord"][]>([]),
    [reviewContext, setReviewContext] = useState<S["ReviewContext"] | null>(
      null,
    ),
    [reconciliations, setReconciliations] = useState<S["Reconciliation"][]>([]);
  const processing = !!job && ["queued", "running"].includes(job.status);
  const root = deal ? "deals/" + deal.id : "workspaces/" + w.id;
  const revision = deal?.revision || w.revision;
  const date = (value: string) =>
    formatDate(value, deal?.owner_timezone || w.owner_timezone);
  const roles =
    session.memberships.find(
      (m) => m.organization_id === session.organization_id,
    )?.roles || [];
  const editor = roles.some((r) => r === "owner" || r === "export_admin");
  const finance = roles.some((r) => r === "owner" || r === "finance_reviewer");
  async function list<K extends keyof S>(path: string): Promise<S[K][]> {
    const rows: S[K][] = [];
    let cursor: string | null = null;
    const seen = new Set<string>();
    do {
      const page: { items: S[K][]; next_cursor: string | null } = await api(
        path +
          "?limit=100" +
          (cursor ? "&cursor=" + encodeURIComponent(cursor) : ""),
      );
      rows.push(...page.items);
      cursor = page.next_cursor;
      if (cursor && seen.has(cursor))
        throw new Error("Pagination tidak bergerak; muat ulang ruang kerja.");
      if (cursor) seen.add(cursor);
    } while (cursor);
    return rows.sort((a, b) => {
      const left = a as { created_at?: string; id?: string };
      const right = b as { created_at?: string; id?: string };
      return (
        (left.created_at || "").localeCompare(right.created_at || "") ||
        (left.id || "").localeCompare(right.id || "")
      );
    });
  }
  async function refresh() {
    const nw = await api<W>("workspaces/" + w.id);
    setW(nw);
    onWorkspace(nw);
    const nd = nw.deal_id
      ? (await api<S["DealResult"]>("deals/" + nw.deal_id)).deal
      : null;
    setDeal(nd);
    const r = nd ? "deals/" + nd.id : "workspaces/" + nw.id;
    await Promise.all([
      list<"Analysis">(r + "/analyses").then(setAnalyses),
      list<"Evidence">(r + "/evidence").then(setEvidence),
      list<"Document">("workspaces/" + nw.id + "/documents").then(setDocs),
      list<"FactCandidate">(r + "/fact-candidates").then(setFacts),
      list<"CostLine">(r + "/cost-lines").then(setCosts),
      list<"FxObservation">(r + "/fx-observations").then(setFx),
    ]);
    if (nd)
      await Promise.all([
        list<"Requirement">(r + "/requirements").then(setRequirements),
        list<"Artifact">(r + "/artifacts").then(setArtifacts),
        list<"FundingOption">(r + "/finance-options").then(setFunding),
        list<"FinanceProduct">(r + "/finance-products").then(
          setFinanceProducts,
        ),
        list<"FinancePack">(r + "/finance-packs").then(setFinancePacks),
        list<"Obligation">(r + "/obligations").then(setObligations),
        list<"Receipt">(r + "/receipts").then(setReceipts),
        list<"Milestone">(r + "/milestones").then(setMilestones),
        list<"AuditRecord">("audit").then(setAudit),
        api<S["Gate"]>(r + "/readiness?stage=shipment").then(setGate),
        api<S["ReviewContext"]>(r + "/review-context").then(setReviewContext),
        list<"Reconciliation">(r + "/reconciliations").then(setReconciliations),
      ]);
  }
  useEffect(() => {
    setLoaded(false);
    refresh()
      .then(() => setLoaded(true))
      .catch((e) => setError(e.message));
  }, [workspace.id]);
  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.status)) return;
    const timer = setTimeout(async () => {
      try {
        const next = await api<S["Run"]>("runs/" + job.id);
        if (!["queued", "running"].includes(next.status)) await refresh();
        setJob(next);
      } catch (e) {
        setError((e as Error).message);
      }
    }, 1000);
    return () => clearTimeout(timer);
  }, [job]);
  async function command(path: string, body: unknown, method = "POST") {
    if (processing && path !== "runs/" + job?.id + "/cancel") {
      setError("Tunggu pekerjaan selesai sebelum mengubah masukan terkait.");
      return null;
    }
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const r = await api<unknown>(path, body, method);
      const accepted = r as { run?: S["Run"]; job?: S["JobAccepted"] };
      if (accepted?.run || accepted?.job?.run)
        setLastRun(
          body instanceof FormData
            ? null
            : { path, body: body as Record<string, unknown> },
        );
      await refresh();
      setMessage("Tersimpan.");
      return r;
    } catch (e) {
      if ((e as Error & { status?: number }).status === 409) {
        try {
          await refresh();
        } catch {}
      }
      setError((e as Error).message);
      return null;
    } finally {
      setBusy(false);
    }
  }
  async function run(path: string, body: unknown) {
    setJob(null);
    const result = (await command(path, body)) as
      | S["JobAccepted"]
      | S["ScenarioAccepted"]
      | null;
    const accepted = result && "job" in result ? result.job : result;
    if (accepted) {
      setJob(accepted.run);
      setMessage("Pekerjaan diterima; menunggu worker.");
    }
  }
  const analysis = analyses.at(-1);
  const confirmed = evidence.filter((e) => e.review_status === "confirmed");
  if (!loaded)
    return (
      <>
        <button className="link" onClick={onBack}>
          ← Semua ruang kerja
        </button>
        <p role="status">{error || "Memuat konteks ruang kerja…"}</p>
      </>
    );
  return (
    <>
      <button className="link" onClick={onBack}>
        ← Semua ruang kerja
      </button>
      <div className="row">
        <div>
          <div className="eyebrow">
            {w.business_profile === "producer" ? "Produsen" : "Reseller"} ·{" "}
            {w.seller_domicile} → {w.destination_country}
          </div>
          <h1>{w.product.description}</h1>
          <p className="muted">
            {deal ? "Transaksi" : "Eksplorasi"} · {w.reporting_currency} ·
            revisi {revision}
          </p>
        </div>
        <span className={"tag " + (w.execution_scope === "demo" ? "demo" : "")}>
          {w.execution_scope === "demo"
            ? "DEMO · SELURUH DATA SINTETIS"
            : "RUANG ORGANISASI"}
        </span>
      </div>
      {deal && (
        <div className="actions">
          {Object.entries(deal.states).map(([k, v]) => (
            <span key={k} className="status">
              {title(k)}: {title(v)}
            </span>
          ))}
        </div>
      )}
      <nav className="tabs" aria-label="Bagian ruang kerja">
        {[
          "Ringkasan",
          "Bukti & dokumen",
          "Biaya & arus kas",
          "Skenario & pendanaan",
          "Draf & persetujuan",
          "Kesiapan & jadwal",
          "Pembayaran & penutupan",
          "Riwayat",
        ].map((t) => (
          <button
            className={tab === t ? "active" : ""}
            key={t}
            onClick={() => setTab(t)}
          >
            {t}
          </button>
        ))}
      </nav>
      {error && (
        <div className="notice error" role="alert">
          {error}
        </div>
      )}
      {message && <p role="status">{message}</p>}
      {job && (
        <section
          className="notice"
          aria-live="polite"
          data-testid="job-state"
          data-status={job.status}
        >
          Pekerjaan {title(job.status)} <code>{job.id}</code>
          {["queued", "running"].includes(job.status) && (
            <button
              className="link"
              onClick={async () => {
                const cancelled = (await command(
                  "runs/" + job.id + "/cancel",
                  {},
                )) as S["Run"] | null;
                if (cancelled) setJob(cancelled);
              }}
            >
              Batalkan
            </button>
          )}
          {["failed", "cancelled"].includes(job.status) &&
            lastRun &&
            editor && (
              <button
                disabled={busy}
                onClick={() =>
                  run(lastRun.path, {
                    ...lastRun.body,
                    expected_revision: revision,
                    ...(lastRun.body.base_revision
                      ? { base_revision: { id: deal?.id || w.id, revision } }
                      : {}),
                  })
                }
              >
                Ulangi dengan revisi terbaru
              </button>
            )}
          <Issues items={[...(job.blockers || []), ...(job.warnings || [])]} />
          {!!job.provider_receipts?.length && (
            <details>
              <summary>Jejak akses sumber dan penyedia</summary>
              {job.provider_receipts.map((receipt, index) => (
                <p key={index}>
                  {receipt.provider} · {receipt.status} ·{" "}
                  {receipt.data_mode || "tidak ada data"}
                  <br />
                  {receipt.fetched_at} ·{" "}
                  {receipt.request_id || "ID penyedia tidak tersedia"}
                  <br />
                  {receipt.limitations.join(" · ")}
                  {receipt.retry_after !== null && (
                    <> · Jendela ulang penyedia: {receipt.retry_after} detik</>
                  )}
                  {receipt.source_url && (
                    <>
                      <br />
                      <a
                        href={receipt.source_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Buka sumber asli
                      </a>
                    </>
                  )}
                </p>
              ))}
            </details>
          )}
        </section>
      )}
      {tab === "Ringkasan" && (
        <>
          <div className="split">
            <section className="card">
              <h2>Fakta produk</h2>
              <p>{w.product.description}</p>
              <p className="muted">
                {w.dispatch_country} → {w.destination_country}
                <br />
                Zona waktu pemilik: {w.owner_timezone}
              </p>
              {editor && (
                <form
                  onSubmit={async (e) => {
                    e.preventDefault();
                    const f = new FormData(e.currentTarget);
                    await command(
                      "workspaces/" + w.id + "/facts",
                      {
                        expected_revision: w.revision,
                        patches: [
                          {
                            op: "replace",
                            reason: "Deskripsi produk diperbarui pemilik",
                            agreement_required_from: [],
                            path: "/product",
                            value: {
                              ...w.product,
                              description: String(f.get("product")),
                            },
                            evidence_ids: [],
                          },
                        ],
                      },
                      "PATCH",
                    );
                  }}
                >
                  <Field
                    name="product"
                    label="Deskripsi produk"
                    value={w.product.description}
                  />
                  <button disabled={busy || processing}>
                    Simpan perubahan
                  </button>
                </form>
              )}
            </section>
            <section className="card">
              <h2>Analisis terakhir</h2>
              {analysis ? (
                <>
                  <span className="tag">{title(analysis.completeness)}</span>
                  {analysis.current_for_use === false && (
                    <span className="status">
                      Masukan berubah / sumber kedaluwarsa
                    </span>
                  )}
                  <p>
                    Kontribusi:{" "}
                    <strong>
                      {money(analysis.after_financing.contribution)}
                    </strong>
                  </p>
                  <p className="muted">
                    {date(analysis.created_at)}
                    <br />
                    Kelengkapan berlaku untuk masukan yang dinyatakan.
                  </p>
                  <Issues
                    items={[
                      ...analysis.blockers,
                      ...(analysis.invalidation_reasons || []),
                    ]}
                  />
                </>
              ) : (
                <p className="muted">
                  Tambahkan asumsi perencanaan, lalu hitung melalui worker.
                </p>
              )}
              {editor && (
                <button
                  disabled={busy || processing}
                  onClick={() =>
                    run(root + "/analyses", {
                      expected_revision: revision,
                      scenario_id: null,
                      scope: "full",
                      execution: "deterministic",
                    })
                  }
                >
                  Hitung ulang analisis
                </button>
              )}
            </section>
          </div>
          {!deal && editor && (
            <>
              <Planning w={w} command={command} evidence={confirmed} />
              {w.planning_inputs && (
                <section className="card">
                  <h2>Lanjutkan ke transaksi</h2>
                  <p className="muted">
                    Masukan perencanaan dipertahankan sebagai sumber. Identitas,
                    jadwal, dan harga masih memerlukan bukti dan persetujuan
                    pihak terkait.
                  </p>
                  <button
                    disabled={busy || processing}
                    onClick={() => {
                      const { cost_lines, fx_observations, ...inputs } =
                        w.planning_inputs!;
                      command("workspaces/" + w.id + "/convert-to-deal", {
                        expected_revision: w.revision,
                        ...inputs,
                      });
                    }}
                  >
                    Buat transaksi dari masukan ini
                  </button>
                </section>
              )}
            </>
          )}
          {deal && (
            <section className="card">
              <h2>Struktur transaksi</h2>
              <div className="grid">
                {deal.parties.map((p) => (
                  <div key={p.id}>
                    <span className="tag">{p.roles.map(title).join(", ")}</span>
                    <p>
                      {p.display_name}
                      <br />
                      <small>{p.country}</small>
                    </p>
                  </div>
                ))}
              </div>
              <p className="muted">
                {deal.line_items.length} baris barang · {deal.shipments.length}{" "}
                pengiriman · {deal.invoices.length} faktur
              </p>
            </section>
          )}
        </>
      )}
      {tab === "Bukti & dokumen" && (
        <>
          {editor && (
            <DiscoveryPanel
              workspace={w}
              disabled={busy || processing}
              run={run}
            />
          )}
          {editor && (
            <SourceEntry
              workspace={w}
              root={root}
              revision={revision}
              documents={docs}
              command={command}
            />
          )}
          <section className="card">
            <h2>Dokumen asli</h2>
            {editor && (
              <form
                onSubmit={async (e) => {
                  e.preventDefault();
                  const f = new FormData(e.currentTarget);
                  f.set("expected_revision", String(w.revision));
                  f.set("document_role", "quotation");
                  const r = (await command(
                    "workspaces/" + w.id + "/documents",
                    f,
                  )) as S["IngestionResponse"]["result"] | null;
                  if (r) setJob(r.job.run);
                }}
              >
                <label>
                  Unggah TXT, PDF, PNG, atau JPEG (maks. 10 MiB)
                  <input
                    name="files"
                    type="file"
                    accept=".txt,.pdf,.png,.jpg,.jpeg"
                    required
                  />
                </label>
                <button disabled={busy || processing}>
                  Unggah dan ekstrak kandidat
                </button>
              </form>
            )}
            {docs.map((d) => (
              <p key={d.id}>
                <a
                  href={
                    "/api/gateway/workspaces/" +
                    w.id +
                    "/documents/" +
                    d.id +
                    "/content"
                  }
                >
                  {d.filename}
                </a>{" "}
                · {title(d.state)} <code>{d.content_hash.slice(0, 16)}</code>
                {editor &&
                  !d.processed_pages &&
                  ["queued", "needs_review"].includes(d.state) && (
                    <button
                      disabled={busy || processing}
                      className="link"
                      onClick={() =>
                        run(
                          "workspaces/" +
                            w.id +
                            "/documents/" +
                            d.id +
                            "/retry",
                          { expected_revision: revision },
                        )
                      }
                    >
                      Coba ekstraksi ulang
                    </button>
                  )}
              </p>
            ))}
          </section>
          <section className="card">
            <h2>Kandidat fakta</h2>
            <p className="muted">
              Hasil ekstraksi tetap memerlukan tinjauan. Konfirmasi sumber tidak
              otomatis mengubah nilai transaksi.
            </p>
            {facts.map((f) => (
              <details key={f.id}>
                <summary>
                  {f.field_path} · {title(f.status)}
                </summary>
                <div className="source">{f.original_text}</div>
                <p>{f.locator}</p>
                {editor && (
                  <div className="actions">
                    {["confirmed", "conflicted", "rejected"].map(
                      (disposition) => (
                        <button
                          className="secondary"
                          key={disposition}
                          disabled={busy || processing}
                          onClick={() =>
                            command(root + "/fact-reviews", {
                              expected_revision: revision,
                              candidate_id: f.id,
                              disposition,
                              patch: null,
                              reason: "Ditinjau melalui ruang kerja",
                            })
                          }
                        >
                          {title(disposition)}
                        </button>
                      ),
                    )}
                  </div>
                )}
              </details>
            ))}
          </section>
          <section className="card">
            <h2>Sumber dan kutipan</h2>
            {evidence.map((s) => (
              <details key={s.id}>
                <summary>
                  {s.title} <span className="tag">{s.mode}</span> ·{" "}
                  {title(s.review_status)}
                </summary>
                <p>
                  {s.publisher} · {date(s.retrieved_at)}
                </p>
                <div className="source">{s.claim}</div>
                <p>Lokasi: {s.locator}</p>
                <p>
                  Berlaku sejak {s.effective_from || "belum dikonfirmasi"} ·
                  hingga {s.valid_until || "belum dikonfirmasi"}
                </p>
                <p>
                  Yurisdiksi sumber:{" "}
                  {s.applicability.jurisdictions.join(", ") || "perlu ditinjau"}{" "}
                  · {s.applicability.validity_reason}
                </p>
                {s.canonical_url && (
                  <a href={s.canonical_url} rel="noreferrer" target="_blank">
                    Sumber publik ↗
                  </a>
                )}
                <p className="muted">{s.limitations.join(" · ")}</p>
                <code>{s.content_hash}</code>
                {editor && (
                  <button
                    className="secondary"
                    disabled={busy || processing}
                    onClick={() =>
                      command(root + "/evidence-reviews", {
                        expected_revision: revision,
                        evidence_id: s.id,
                        disposition: "confirmed",
                        reason: "Sumber ditinjau untuk transaksi ini",
                      })
                    }
                  >
                    Konfirmasi sumber
                  </button>
                )}
              </details>
            ))}
          </section>
        </>
      )}
      {tab === "Biaya & arus kas" && (
        <>
          <section className="card">
            <h2>Biaya yang dinyatakan</h2>
            <div className="scroll">
              <table>
                <thead>
                  <tr>
                    <th>Komponen / perlakuan</th>
                    <th>Estimasi</th>
                    <th>Aktual</th>
                    <th>Sumber</th>
                  </tr>
                </thead>
                <tbody>
                  {costs.map((c) => (
                    <tr key={c.id}>
                      <td>
                        {componentTitle(c.component_key, deal)}
                        <br />
                        <small>
                          {title(c.treatment)} · {title(c.status)} · Cakupan:{" "}
                          {c.covered_components
                            .map((key) => componentTitle(key, deal))
                            .join(", ")}
                        </small>
                      </td>
                      <td>
                        {money(
                          analysis?.cost_breakdown?.find(
                            (b) => b.cost_line_ref.id === c.id,
                          )?.reporting_amount || c.estimate.base,
                        )}
                      </td>
                      <td>{money(c.actual_amount)}</td>
                      <td>
                        {c.evidence_ids.map((id) => (
                          <a
                            key={id}
                            href="#"
                            onClick={(e) => {
                              e.preventDefault();
                              setTab("Bukti & dokumen");
                            }}
                          >
                            {evidence.find((e) => e.id === id)?.title || id}
                            <br />
                          </a>
                        ))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          {analysis && (
            <>
              <section className="card">
                <h2>Kontribusi dan kebutuhan kas</h2>
                <div className="grid">
                  <Metric
                    label="Kontribusi sesudah pembiayaan"
                    value={money(analysis.after_financing.contribution)}
                  />
                  <Metric
                    label="Kas minimum"
                    value={analysis.cash_metrics?.minimum_cash}
                  />
                  <Metric
                    label="Kekurangan buffer"
                    value={analysis.cash_metrics?.buffer_shortfall}
                  />
                  <Metric
                    label="Kas akhir"
                    value={analysis.cash_metrics?.final_cash}
                  />
                </div>
                <p className="muted">
                  {analysis.cash_metrics?.reporting_currency} ·{" "}
                  {title(
                    analysis.cash_metrics?.calculation_scope ||
                      "known_items_only",
                  )}{" "}
                  · horizon{" "}
                  {analysis.cash_metrics &&
                    date(analysis.cash_metrics.horizon_end)}
                </p>
                <Issues items={[...analysis.blockers, ...analysis.warnings]} />
                <h3>Urutan arus kas dari server</h3>
                <div className="scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Waktu</th>
                        <th>Arah</th>
                        <th>Jumlah</th>
                        <th>Saldo sesudah kejadian</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analysis.cash_metrics?.event_balances?.map((p, n) => (
                        <tr key={n}>
                          <td>{date(p.at)}</td>
                          <td>{p.direction === "in" ? "Masuk" : "Keluar"}</td>
                          <td>{money(p.amount)}</td>
                          <td>{money(p.balance)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <h3>Interval kas negatif</h3>
                {analysis.cash_metrics?.negative_intervals.map((i, n) => (
                  <p key={n}>
                    {date(i.start)} →{" "}
                    {i.end ? date(i.end) : "Masih terbuka pada akhir horizon"}
                  </p>
                ))}
                <h3>Harga dan pembanding</h3>
                <div className="grid">
                  <Metric
                    label="Harga dasar penjual per satuan"
                    value={analysis.price_range.seller_floor || undefined}
                  />
                  <Metric
                    label="Pembanding pasar rendah"
                    value={analysis.price_range.market_low || undefined}
                  />
                  <Metric
                    label="Pembanding pasar tinggi"
                    value={analysis.price_range.market_high || undefined}
                  />
                </div>
                <p className="muted">
                  {analysis.price_range.currency} / {analysis.price_range.unit}
                </p>
                {analysis.price_range.assumptions.map((v, n) => (
                  <p className="notice" key={n}>
                    {v}
                  </p>
                ))}
                {analysis.price_range.rejected_comparators.map((c) => (
                  <p key={c.id} className="muted">
                    Pembanding dikeluarkan: {c.reason}
                  </p>
                ))}
                <p className="muted">
                  {title(analysis.price_range.label)} · Pembanding yang tidak
                  sebanding tidak menjadi harga transaksi.
                </p>
                <Lineage analysis={analysis} />
                <code>
                  Analisis {analysis.snapshot_hash} ·{" "}
                  {analysis.calculator_version}
                </code>
              </section>
            </>
          )}
        </>
      )}
      {tab === "Skenario & pendanaan" && (
        <>
          {deal && editor && (
            <ScenarioEditor
              deal={deal}
              funding={funding}
              disabled={busy || processing}
              command={command}
              run={run}
            />
          )}
          <section className="card">
            <h2>Pembiayaan: persiapan saja</h2>
            <p className="muted">
              Penawaran hipotetis tidak membuktikan ketersediaan dana, kelayakan
              pemberi pinjaman, atau pencairan.
            </p>
            {deal && editor && (
              <button
                disabled={busy || processing}
                onClick={() =>
                  run(root + "/finance-options", {
                    expected_revision: revision,
                    analysis_id: analysis?.id,
                    company: {
                      seller_party_id: deal.parties.find((p) =>
                        p.roles.includes("seller"),
                      )?.id,
                      registration_evidence_ids: [],
                      financial_evidence_ids: [],
                      unknowns: [],
                    },
                    requested_amount: null,
                    required_by: null,
                  })
                }
              >
                Cari opsi pendanaan
              </button>
            )}
            {funding.map((f) => (
              <article key={f.id}>
                <h3>
                  {money(f.draw)} <span className="tag">{title(f.fit)}</span>
                </h3>
                <p>{f.fit_reasons.join(" · ")}</p>
                <div className="timeline">
                  {f.schedule.map((event, n) => (
                    <article key={n}>
                      {title(event.kind)} · {money(event.amount)}
                      <br />
                      <small>
                        {event.schedule.kind === "fixed"
                          ? ("instant" in event.schedule.due
                              ? formatDate(
                                  event.schedule.due.instant,
                                  event.schedule.due.timezone,
                                )
                              : event.schedule.due.date) +
                            " · " +
                            event.schedule.due.timezone
                          : "Relatif terhadap peristiwa"}
                      </small>
                    </article>
                  ))}
                </div>
                {editor && deal && (
                  <button
                    className="secondary"
                    disabled={busy || processing}
                    onClick={async () => {
                      setJob(null);
                      const r = (await command(root + "/scenarios", {
                        expected_revision: revision,
                        base_revision: { id: deal.id, revision },
                        patches: [],
                        funding_option_ids: [f.id],
                      })) as S["ScenarioJobResponse"]["result"] | null;
                      if (r) setJob(r.job.run);
                    }}
                  >
                    Hitung skenario pendanaan ini
                  </button>
                )}
              </article>
            ))}
          </section>
          <section className="card">
            <h2>Perbandingan skenario</h2>
            {analyses.map((a) => (
              <p key={a.id}>
                <code>{a.scenario_id}</code>
                <br />
                {money(a.after_financing.contribution)} · kas minimum{" "}
                {a.cash_metrics?.minimum_cash} · {title(a.completeness)}
                {a.owner_comparison && (
                  <>
                    <br />
                    Peringkat relatif:{" "}
                    {a.owner_comparison.rank || "belum tersedia"} · preferensi{" "}
                    {a.owner_comparison.ranking_preference || "belum dipilih"}
                    <br />
                    {a.owner_comparison.checks.map((check) => (
                      <span className="tag" key={check.code}>
                        {check.code}: {title(check.status)}
                      </span>
                    ))}
                    <br />
                    Pihak yang perlu menerima:{" "}
                    {a.owner_comparison.required_counterparty_ids
                      .map(
                        (id) =>
                          deal?.parties.find((p) => p.id === id)
                            ?.display_name || id,
                      )
                      .join(", ") || "sesuai penerimaan kontrak yang berlaku"}
                    <br />
                    <small>{a.owner_comparison.basis}</small>
                  </>
                )}
              </p>
            ))}
          </section>
        </>
      )}
      {tab === "Draf & persetujuan" && (
        <>
          <section className="card">
            <h2>Draf komersial</h2>
            <p className="muted">
              Draf dapat diunduh dan ditinjau. Placeholder harus diselesaikan
              sebelum digunakan.
            </p>
            {deal && analysis && editor && (
              <>
                <label>
                  Jenis draf
                  <select
                    value={draftKind}
                    onChange={(event) =>
                      setDraftKind(event.target.value as S["ArtifactKind"])
                    }
                  >
                    <option value="agreement">Perjanjian</option>
                    <option value="message">Pesan untuk pihak terkait</option>
                    <option value="recommendation">Rekomendasi internal</option>
                    <option value="clause_revision">Usulan klausul</option>
                    <option value="amendment">
                      Usulan perubahan perjanjian
                    </option>
                  </select>
                </label>
                <label>
                  Bahasa draf
                  <select
                    value={draftLanguage}
                    onChange={(event) => setDraftLanguage(event.target.value)}
                  >
                    <option value="id">Bahasa Indonesia</option>
                    <option value="en">English</option>
                  </select>
                </label>
                <label>
                  Penerima draf
                  <select
                    value={draftRecipient}
                    onChange={(event) => setDraftRecipient(event.target.value)}
                  >
                    <option value="">Sesuai konteks draf</option>
                    {deal.parties.map((party) => (
                      <option key={party.id} value={party.id}>
                        {party.display_name}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  disabled={busy || processing}
                  onClick={() =>
                    run(root + "/drafts", {
                      expected_revision: revision,
                      scenario_id: analysis.scenario_id,
                      analysis_id: analysis.id,
                      kind: draftKind,
                      recipient_party_id: draftRecipient || null,
                      language: draftLanguage,
                    })
                  }
                >
                  Buat draf dari analisis
                </button>
              </>
            )}
            {artifacts.map((a) => (
              <details key={a.id}>
                <summary>
                  {title(a.kind)} · {title(a.state)}
                </summary>
                <div className="source">{a.content}</div>
                <p>Placeholder: {a.placeholders.join(", ")}</p>
                <code>{a.content_hash}</code>
                <p>
                  <a
                    href={
                      "/api/gateway/" + root + "/artifacts/" + a.id + "/content"
                    }
                  >
                    Unduh draf
                  </a>
                </p>
              </details>
            ))}
          </section>
          {deal && analysis && roles.includes("owner") && (
            <section className="card">
              <h2>Tinjauan pemilik</h2>
              <p className="muted">
                Berlaku untuk hash analisis dan bukti saat ini. Tidak
                menggantikan penerimaan pihak lain atau verifikasi dana.
              </p>
              <button
                disabled={busy || processing}
                onClick={() =>
                  command(root + "/approvals", {
                    expected_revision: revision,
                    purpose: "plan",
                    analysis_hash: analysis.snapshot_hash,
                    evidence_digest: analysis.evidence_digest,
                    artifact_hash: null,
                    decision: "approved",
                  })
                }
              >
                Catat persetujuan rencana
              </button>
            </section>
          )}
        </>
      )}
      {tab === "Kesiapan & jadwal" && (
        <>
          <section className="card">
            <h2>Gerbang kesiapan pengiriman</h2>
            {gate ? (
              <>
                <span className="status">{title(gate.status)}</span>
                {gate.conditions.map((c) => (
                  <div className="notice" key={c.code}>
                    <strong>
                      {c.status === "satisfied" ? "✓" : "○"} {c.code}
                    </strong>
                    <br />
                    {c.reason}
                    {c.evidence_refs.map((ref) => {
                      const source = evidence.find((row) => row.id === ref.id);
                      return source ? (
                        <details key={ref.id}>
                          <summary>Bukti: {source.title}</summary>
                          <p>
                            {source.publisher} · {title(source.mode)} ·{" "}
                            {title(source.review_status)} · {source.locator}
                          </p>
                          <blockquote>{source.claim}</blockquote>
                          <p>
                            Berlaku sampai:{" "}
                            {source.valid_until || "Tidak dinyatakan"}
                          </p>
                          {source.document_id && (
                            <a
                              href={
                                "/api/gateway/workspaces/" +
                                w.id +
                                "/documents/" +
                                source.document_id +
                                "/content"
                              }
                            >
                              Unduh sumber asli
                            </a>
                          )}
                        </details>
                      ) : (
                        <p key={ref.id}>
                          Sumber {ref.id} · lihat riwayat yang diizinkan
                        </p>
                      );
                    })}
                  </div>
                ))}
              </>
            ) : (
              <p className="muted">
                Tersedia setelah konversi menjadi transaksi.
              </p>
            )}
          </section>
          {deal && roles.includes("owner") && (
            <CalendarPanel
              deal={deal}
              milestones={milestones}
              demo={w.execution_scope === "demo"}
              disabled={busy || processing}
              command={command}
              run={run}
            />
          )}
          <section className="card">
            <h2>Persyaratan</h2>
            {requirements.map((r) => (
              <article key={r.id}>
                <h3>{r.category}</h3>
                <p>
                  {title(r.applicability)} · {title(r.fulfillment_status)}
                </p>
                <p className="muted">
                  {r.evidence_ids.length} sumber ·{" "}
                  {r.fulfillment_evidence_ids.length} bukti pemenuhan
                </p>
              </article>
            ))}
          </section>
          <section className="card">
            <h2>Jadwal internal</h2>
            <div className="timeline">
              {milestones.map((m) => (
                <article key={m.id}>
                  <strong>{title(m.kind)}</strong>
                  <p>
                    {m.schedule.kind === "fixed"
                      ? "Tanggal tetap"
                      : "Relatif terhadap " + m.schedule.anchor_milestone_id}
                  </p>
                  {m.resolved_forecast && (
                    <p>
                      {"date" in m.resolved_forecast
                        ? m.resolved_forecast.date +
                          " · " +
                          m.resolved_forecast.timezone
                        : date(m.resolved_forecast.instant)}
                    </p>
                  )}
                  <Issues items={m.resolution_issues || []} />
                  {m.actual && <span className="tag">Aktual diverifikasi</span>}
                </article>
              ))}
            </div>
            {milestones.length === 0 && (
              <p className="muted">
                Belum ada milestone tercatat. Tanggal pembayaran berada pada
                kewajiban masing-masing.
              </p>
            )}
          </section>
        </>
      )}
      {tab === "Pembayaran & penutupan" && (
        <>
          <section className="card">
            <h2>Kewajiban dan bukti pembayaran</h2>
            <p className="muted">
              Pembeli lunas dan penutupan internal adalah dua status terpisah.
              Bukti pending tidak melunasi kewajiban.
            </p>
            <div className="scroll">
              <table>
                <thead>
                  <tr>
                    <th>Kewajiban</th>
                    <th>Jumlah</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {obligations.map((o) => (
                    <tr key={o.id}>
                      <td>
                        {o.id}
                        <br />
                        <small>
                          {o.payer_party_id} → {o.payee_party_id}
                        </small>
                      </td>
                      <td>{money(o.amount)}</td>
                      <td>{title(o.status)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {receipts.map((r) => (
              <p key={r.id}>
                {money(r.received_amount)} · {r.value_date} ·{" "}
                <strong>{title(r.status)}</strong>{" "}
                {r.supersedes && <small>Menggantikan {r.supersedes}</small>}
              </p>
            ))}
            {deal && finance && (
              <ReceiptForm
                obligations={obligations}
                evidence={confirmed}
                revision={revision}
                root={root}
                command={command}
              />
            )}
          </section>
          {deal && finance && (
            <section className="card">
              <h2>Rekonsiliasi internal</h2>
              {reconciliations.map((r) => (
                <details key={r.id}>
                  <summary>
                    {date(r.created_at)} · {title(r.closure_gate.status)}
                  </summary>
                  <p>Kontribusi aktual: {money(r.actual_contribution)}</p>
                  <p>
                    {r.unresolved_obligation_ids.length} kewajiban belum selesai
                  </p>
                  <Issues items={r.unresolved_disputes} />
                  {r.dimensions?.map((row, n) => (
                    <p key={n}>
                      {title(row.category)} · {title(row.baseline_kind)} ·{" "}
                      {row.baseline_value ?? "Belum diketahui"} →{" "}
                      {row.actual_value ?? "Belum diketahui"} {row.unit}
                      <br />
                      <small>{row.basis}</small>
                    </p>
                  ))}
                  <div className="scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Komponen</th>
                          <th>Baseline</th>
                          <th>Aktual</th>
                          <th>Selisih</th>
                        </tr>
                      </thead>
                      <tbody>
                        {r.variances.map((v, n) => (
                          <tr key={n}>
                            <td>
                              {title(v.category)} ·{" "}
                              {title(v.baseline_kind || "initial")}
                            </td>
                            <td>{money(v.baseline)}</td>
                            <td>{money(v.actual)}</td>
                            <td>{money(v.difference)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </details>
              ))}
              {reconciliations.length > 0 && (
                <button
                  className="secondary"
                  disabled={busy || processing}
                  onClick={async () => {
                    const r = (await command(root + "/close", {
                      expected_revision: revision,
                      reconciliation_hash:
                        reconciliations.at(-1)!.reconciliation_hash,
                    })) as S["ClosureResult"] | null;
                    if (r) {
                      setGate(r.gate);
                      setMessage(
                        r.gate.status === "blocked"
                          ? "Penutupan masih terblokir. Tinjau kondisi gerbang."
                          : "Transaksi ditutup setelah seluruh syarat terpenuhi.",
                      );
                    }
                  }}
                >
                  Evaluasi penutupan internal
                </button>
              )}

              <p className="muted">
                Bandingkan aktual dengan baseline yang dipertahankan. Penutupan
                tetap diblokir selama syarat belum terpenuhi.
              </p>
              <button
                disabled={busy || processing}
                onClick={() =>
                  command(root + "/reconcile", {
                    expected_revision: revision,
                    actual_evidence_ids: confirmed.map((e) => e.id),
                    adjustments: [],
                  })
                }
              >
                Jalankan rekonsiliasi
              </button>
            </section>
          )}
        </>
      )}
      {deal && editor && tab === "Ringkasan" && (
        <fieldset disabled={busy || processing}>
          <PartyEntry deal={deal} evidence={confirmed} command={command} />
          <OwnerEntry deal={deal} evidence={confirmed} command={command} />
        </fieldset>
      )}
      {deal &&
        roles.some(
          (role) => role === "owner" || role === "production_procurement",
        ) &&
        tab === "Kesiapan & jadwal" && (
          <fieldset disabled={busy || processing}>
            <RuleEntry deal={deal} evidence={confirmed} command={command} />
          </fieldset>
        )}
      {deal && finance && tab === "Skenario & pendanaan" && (
        <fieldset disabled={busy || processing}>
          <FinanceEntry
            deal={deal}
            evidence={confirmed}
            analysis={analysis}
            products={financeProducts}
            packs={financePacks}
            funding={funding}
            command={command}
            run={run}
          />
        </fieldset>
      )}
      {deal &&
        (tab === "Biaya & arus kas" ||
          (finance && tab === "Pembayaran & penutupan")) && (
          <fieldset disabled={busy || processing}>
            <FinancialEntry
              deal={deal}
              evidence={confirmed}
              obligations={obligations}
              costs={costs}
              fx={fx}
              finance={finance && tab === "Pembayaran & penutupan"}
              showCosts={tab === "Biaya & arus kas"}
              command={command}
            />
          </fieldset>
        )}
      {deal && (
        <ReviewControls
          deal={deal}
          tab={tab}
          context={reviewContext}
          evidence={confirmed}
          requirements={requirements}
          costs={costs}
          receipts={receipts}
          milestones={milestones}
          fx={fx}
          command={command}
          editor={editor}
          finance={finance}
          production={
            roles.includes("owner") || roles.includes("production_procurement")
          }
        />
      )}
      {tab === "Riwayat" && (
        <section className="card">
          <h2>Jejak perubahan</h2>
          <p>
            <a href={"/api/gateway/" + root + "/export"}>
              Unduh snapshot, bukti, dan riwayat
            </a>
          </p>
          {audit.map((a) => (
            <p key={a.id}>
              <strong>{a.action}</strong>
              <br />
              <small>
                {date(a.created_at)} · {a.created_by}
              </small>
            </p>
          ))}
          {audit.length === 0 && (
            <p className="muted">
              Riwayat transaksi belum tersedia pada tampilan ini.
            </p>
          )}
        </section>
      )}
    </>
  );
}
function Metric({ label, value }: { label: string; value?: string }) {
  return (
    <div className="metric">
      <small>{label}</small>
      <strong>{value || "Belum diketahui"}</strong>
    </div>
  );
}
type Command = (
  path: string,
  body: unknown,
  method?: string,
) => Promise<unknown>;
function Planning({
  w,
  command,
  evidence,
}: {
  w: W;
  command: Command;
  evidence: S["Evidence"][];
}) {
  const [error, setError] = useState("");
  return (
    <form
      className="card"
      onSubmit={async (e: FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        const m = (key: string) =>
          f.get(key)
            ? { amount: String(f.get(key)), currency: w.reporting_currency }
            : null;
        const cashKeys = ["cash", "committed", "buffer", "cash_date"];
        if (
          cashKeys.some((key) => f.get(key)) &&
          !cashKeys.every((key) => f.get(key))
        ) {
          setError(
            "Lengkapi saldo, komitmen, cadangan dan waktu saldo bersama; nilai kosong tidak dianggap nol.",
          );
          return;
        }
        setError("");
        await command("workspaces/" + w.id + "/planning-estimate", {
          expected_revision: w.revision,
          quantity: String(f.get("quantity")),
          unit: String(f.get("unit")),
          unit_cost: m("cost"),
          invoice_amount: m("invoice"),
          deposit_amount: m("deposit"),
          deposit_at: null,
          balance_at: null,
          supplier_payment_at: null,
          local_payment_times: {
            ...(f.get("deposit_at")
              ? { deposit: String(f.get("deposit_at")) }
              : {}),
            ...(f.get("balance_at")
              ? { balance: String(f.get("balance_at")) }
              : {}),
            ...(f.get("cost_at") ? { supplier: String(f.get("cost_at")) } : {}),
          },
          cash_snapshot: null,
          ...(f.get("cash_date")
            ? {
                local_cash_snapshot: {
                  available: m("cash"),
                  committed_elsewhere: m("committed"),
                  minimum_buffer: m("buffer"),
                  local_datetime: String(f.get("cash_date")),
                },
              }
            : {}),
          target_margin: null,
          target_margin_percent: f.get("margin")
            ? String(f.get("margin"))
            : null,
          evidence_ids: f.getAll("evidence").map(String),
        });
      }}
    >
      <h2>Asumsi awal perencanaan</h2>
      <p className="muted">
        Semua nilai dalam {w.reporting_currency}. Masukan yang belum ada tetap
        tidak diketahui. Waktu skenario memakai zona {w.owner_timezone}; tidak
        ada waktu yang diasumsikan dari tanggal saja.
      </p>
      <div className="grid">
        <Field name="quantity" label="Jumlah" value="10" />
        <Field name="unit" label="Satuan" value="kg" />
        <Field name="cash" label="Saldo awal tersedia" required={false} />
        <Field
          name="committed"
          label="Dana terikat di luar transaksi"
          required={false}
        />
        <Field
          name="buffer"
          label="Buffer minimum yang Anda pilih"
          required={false}
        />
        <Field
          name="cash_date"
          label="Waktu saldo pada zona pemilik"
          type="datetime-local"
          required={false}
        />
        <Field
          name="margin"
          label="Target margin kontribusi (%)"
          required={false}
        />
        <Field name="cost" label="Biaya per satuan" required={false} />
        <Field name="invoice" label="Total faktur pembeli" required={false} />
        <Field name="deposit" label="Uang muka pembeli" required={false} />
        <Field
          name="deposit_at"
          label="Waktu skenario uang muka"
          type="datetime-local"
          required={false}
        />
        <Field
          name="balance_at"
          label="Waktu skenario pelunasan pembeli"
          type="datetime-local"
          required={false}
        />
        <Field
          name="cost_at"
          label="Waktu skenario pembayaran input"
          type="datetime-local"
          required={false}
        />
      </div>
      <label>
        Sumber yang mendasari asumsi ini
        <select name="evidence" multiple>
          {evidence.map((source) => (
            <option key={source.id} value={source.id}>
              {source.title}
            </option>
          ))}
        </select>
      </label>
      {error && <p role="alert">{error}</p>}
      <button>Simpan asumsi perencanaan</button>
    </form>
  );
}
function ReceiptForm({
  obligations,
  evidence,
  revision,
  root,
  command,
}: {
  obligations: S["Obligation"][];
  evidence: S["Evidence"][];
  revision: number;
  root: string;
  command: Command;
}) {
  return (
    <details>
      <summary>Catat bukti pembayaran pending</summary>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          const f = new FormData(e.currentTarget);
          const obligation = obligations.find(
            (o) => o.id === f.get("obligation"),
          );
          if (!obligation?.amount) return;
          const amount = {
            amount: String(f.get("amount")),
            currency: obligation.amount.currency,
          };
          await command(root + "/receipts", {
            expected_revision: revision,
            received_amount: amount,
            value_date: String(f.get("date")),
            allocations: [{ obligation_id: obligation.id, amount }],
            evidence_ids: [String(f.get("evidence"))],
          });
        }}
      >
        <label>
          Kewajiban
          <select name="obligation">
            {obligations.map((o) => (
              <option value={o.id} key={o.id}>
                {o.id} · {money(o.amount)}
              </option>
            ))}
          </select>
        </label>
        <Field name="amount" label="Jumlah diterima" />
        <Field name="date" label="Tanggal nilai" type="date" />
        <label>
          Bukti yang sudah ditinjau
          <select name="evidence" required>
            {evidence.map((e) => (
              <option key={e.id} value={e.id}>
                {e.title}
              </option>
            ))}
          </select>
        </label>
        <button disabled={!evidence.length}>Simpan bukti pending</button>
      </form>
    </details>
  );
}
function Settings() {
  const [data, setData] = useState<S["Entitlement"] | null>(null);
  useEffect(() => {
    api<S["Entitlement"]>("entitlements")
      .then(setData)
      .catch(() => {});
  }, []);
  return data ? (
    <details className="card">
      <summary>Penggunaan & paket · {data.plan}</summary>
      <p>{title(data.status)}</p>
      <p>
        Slot transaksi aktif: {data.active_deals} / {data.active_deal_limit} ·
        batas anggota {data.user_limit}
      </p>
      {data.allowances.map((a) => (
        <p key={a.unit}>
          {title(a.unit)}: {a.included_remaining} tersisa · tambahan{" "}
          {a.addon_remaining} · berlaku hingga{" "}
          {a.expires_at || "sesuai periode paket"}
        </p>
      ))}
      <p className="muted">
        Perhitungan deterministik dan pencatatan pembayaran manual tidak memakai
        jatah pencarian diperkaya.
      </p>
    </details>
  ) : null;
}

function Lineage({ analysis }: { analysis: A }) {
  const [source, setSource] = useState<
      S["InputRevisionResponse"]["result"] | null
    >(null),
    [error, setError] = useState("");
  return (
    <details>
      <summary>Telusuri rumus dan versi sumber</summary>
      {analysis.numeric_lineage?.map((line, n) => (
        <article key={n}>
          <h3>{title(line.metric)}</h3>
          <p>{line.formula}</p>
          <small>{line.calculator_version}</small>
          <div className="actions">
            {line.evidence_refs.map((ref) => (
              <button
                key={ref.id}
                className="link"
                onClick={() =>
                  api<S["InputRevisionResponse"]["result"]>(
                    "inputs/" + ref.id + "/revisions/" + ref.revision,
                  )
                    .then(setSource)
                    .catch((e) => setError(e.message))
                }
              >
                Sumber revisi {ref.revision} · {ref.id.slice(-8)}
              </button>
            ))}
          </div>
          <p className="muted">
            {line.input_refs.length} masukan versi tetap; perubahan berikutnya
            tidak menimpa analisis ini.
          </p>
        </article>
      ))}
      {!analysis.numeric_lineage && (
        <p className="muted">
          Hitung ulang untuk mendapatkan referensi versi sumber.
        </p>
      )}
      {source && "claim" in source && (
        <aside className="source">
          <strong>{source.title}</strong>
          <p>{source.claim}</p>
          <small>{source.locator}</small>
          <br />
          <code>{source.content_hash}</code>
        </aside>
      )}
      {error && <p role="alert">{error}</p>}
    </details>
  );
}

function MemberAdmin({
  session,
  onChanged,
}: {
  session: S["Session"];
  onChanged: () => Promise<void>;
}) {
  const [members, setMembers] = useState<S["Membership"][]>([]),
    [error, setError] = useState(""),
    [message, setMessage] = useState("");
  const root = "organizations/" + session.organization_id + "/memberships";
  async function refresh() {
    setMembers((await api<S["MembershipPage"]>(root)).items);
  }
  useEffect(() => {
    refresh().catch((error) => setError(error.message));
  }, [root]);
  const roles: S["Role"][] = [
    "owner",
    "export_admin",
    "finance_reviewer",
    "production_procurement",
  ];
  return (
    <details className="card">
      <summary>Anggota dan izin organisasi</summary>
      <p>
        Gunakan ID akun lokal yang telah dibuat oleh operator. Mengosongkan
        semua peran mencabut keanggotaan; organisasi harus tetap memiliki
        pemilik.
      </p>
      {error && <p role="alert">{error}</p>}
      {message && <p role="status">{message}</p>}
      {members.map((member) => (
        <p key={member.id}>
          <code>{member.user_id || member.id}</code> ·{" "}
          {member.roles.map(title).join(", ")}
        </p>
      ))}
      <form
        onSubmit={async (event) => {
          event.preventDefault();
          setError("");
          setMessage("");
          const form = new FormData(event.currentTarget);
          try {
            await api(root, {
              user_id: String(form.get("user")),
              roles: form.getAll("roles"),
            });
            await refresh();
            await onChanged();
            setMessage("Izin anggota diperbarui.");
          } catch (error) {
            setError((error as Error).message);
          }
        }}
      >
        <Field name="user" label="ID akun anggota" />
        <fieldset>
          <legend>Peran yang diberikan</legend>
          {roles.map((role) => (
            <label key={role}>
              <input type="checkbox" name="roles" value={role} />
              {title(role)}
            </label>
          ))}
        </fieldset>
        <button>Simpan izin anggota</button>
      </form>
    </details>
  );
}
