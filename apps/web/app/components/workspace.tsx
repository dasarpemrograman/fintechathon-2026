"use client";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { DiscoveryPanel } from "./discovery-panel";
import { ScenarioEditor } from "./scenario-editor";
import { FinancialEntry } from "./financial-entry";
import { FinanceEntry } from "./finance-entry";
import { RuleEntry, OwnerEntry, PartyEntry } from "./deal-entry";
import { CalendarPanel } from "./calendar-panel";
import { SourceEntry } from "./source-entry";
import { ReviewControls } from "./review-controls";
import { HistoryPanel } from "./history-panel";
import {
  AppShell,
  AuthIntroduction,
  Brand,
  Icon,
  type HomeSection,
} from "./app-shell";
import { WorkspacePortfolio } from "./workspace-portfolio";
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
      data.message || data.reason || data.code || "Request failed.",
    ) as Error & { status: number };
    error.status = response.status;
    throw error;
  }
  return data.result as T;
}
const formatDate = (s: string, timezone = "Asia/Jakarta") =>
  new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: timezone,
  }).format(new Date(s));
const money = (m: S["Money"] | S["SignedMoney"] | null | undefined) =>
  m ? m.currency + " " + m.amount : "Not yet known";
const labels: Record<string, string> = {
  analysis: "Analysis",
  commercial_terms: "Agreement",
  funding_preparation: "Funding preparation",
  execution_gate: "Action gate",
  goods: "Goods",
  shipment: "Shipment",
  buyer_payment: "Buyer payment",
  internal_closure: "Closure",
  not_started: "Not started",
  not_booked: "Not booked",
  booking_review: "Booking review",
  booked: "Booking recorded",
  in_transit: "In transit",
  delivered: "Delivered",
  exception: "Exception",
  not_due: "Not due",
  due: "Outstanding",
  verification_pending: "Awaiting verification",
  partially_paid: "Partially paid",
  overdue: "Overdue",
  disputed: "Disputed",
  open: "Open",
  not_needed: "Not required",
  needed: "Required",
  preparing: "Preparing",
  comparing: "Comparing",
  application_ready: "Preparation pack ready for review",
  agreed: "Accepted by relevant parties",
  owner_reviewed: "Owner reviewed",
  awaiting_counterparties: "Awaiting counterparties",
  superseded: "Superseded",
  draft: "Draft",
  scoped_complete: "Complete for this scope",
  expense: "Expense",
  user_assumed: "User assumption",
  quoted: "Quoted",
  published_tariff: "Published tariff",
  modeled: "Estimated",
  unknown: "Not yet known",
  recoverable_tax: "Recoverable tax",
  reimbursable_advance: "Advance",
  capital_allocation: "Capital allocation",
  synthetic_demo: "Synthetic demo",
  cached: "Cached",
  user_provided: "User provided",
  live: "Live source",
  loan_draw: "Loan drawdown",
  principal_repayment: "Principal repayment",
  finance_cost: "Financing cost",
  withheld_fee: "Withheld fee",
  interest: "Interest",
  reserve_release: "Reserve release",
  packaging: "Packaging",
  administration: "Administration",
  origin_trucking: "Origin trucking",
  main_freight: "Main freight",
  destination_delivery: "Destination delivery",
  production: "Production",
  procurement: "Procurement",
  materials: "Materials",
  labor: "Labor",
  process: "Production process",
  overhead: "Allocated overhead",
  analyzed_complete: "Analysis available",
  analyzed_partial: "Partial analysis",
  needs_input: "Inputs needed",
  not_analyzed: "Not analyzed",
  owner: "Owner",
  export_admin: "Export admin",
  finance_reviewer: "Finance reviewer",
  production_procurement: "Production & procurement",
  paid: "Buyer paid",
  resolved_with_writeoff: "Resolved with write-off",
  reconciling: "Internal reconciliation",
  closed: "Closed",
  blocked: "Blocked",
  ready_for_next_action: "Ready for the next action",
  proposed: "Proposed",
  pending: "Awaiting verification",
  verified: "Verified",
  succeeded: "Completed",
  failed: "Failed",
  partial: "Partial",
  cancelled: "Cancelled",
  queued: "Queued",
  running: "Running",
};
const title = (s: string) => labels[s] || s.replaceAll("_", " ");
function componentTitle(key: string, deal: D | null) {
  if (key.startsWith("procurement:")) {
    const line = deal?.line_items.find(
      (row) => row.id === key.slice("procurement:".length),
    );
    return "Procurement" + (line ? " · " + line.product.description : " goods");
  }
  if (key.startsWith("production-input:")) {
    const plan = deal?.procurement;
    const input =
      plan?.business_profile === "producer"
        ? plan.inputs.find(
            (row) => row.id === key.slice("production-input:".length),
          )
        : null;
    return "Production input" + (input ? " · " + input.description : "");
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
  const viewEpoch = useRef(0);
  const [session, setSession] = useState<S["Session"] | null>(null),
    [loading, setLoading] = useState(true),
    [listLoading, setListLoading] = useState(false),
    [authBusy, setAuthBusy] = useState(false),
    [error, setError] = useState(""),
    [identities, setIdentities] = useState<
      S["DemoIdentitiesResponse"]["result"]["users"]
    >([]),
    [workspaces, setWorkspaces] = useState<W[]>([]),
    [selected, setSelected] = useState<W | null>(null),
    [creating, setCreating] = useState(false),
    [homeSection, setHomeSection] = useState<HomeSection>("workspaces"),
    [workspaceCursor, setWorkspaceCursor] = useState<string | null>(null);
  async function load(append = false) {
    const epoch = viewEpoch.current;
    setListLoading(true);
    try {
      const page = await api<S["WorkspacePage"]>(
        "workspaces?limit=25" +
          (append && workspaceCursor
            ? "&cursor=" + encodeURIComponent(workspaceCursor)
            : ""),
      );
      if (epoch !== viewEpoch.current) return;
      setWorkspaces((old) =>
        append
          ? [
              ...old,
              ...page.items.filter(
                (item) => !old.some((row) => row.id === item.id),
              ),
            ]
          : page.items,
      );
      setWorkspaceCursor(page.next_cursor);
    } finally {
      if (epoch === viewEpoch.current) setListLoading(false);
    }
  }
  useEffect(() => {
    api<S["Session"]>("auth/session")
      .then((s) => {
        setSession(s);
        return load();
      })
      .catch(() =>
        api<S["DemoIdentitiesResponse"]["result"]>("auth/demo-identities")
          .then((data) => setIdentities(data.users))
          .catch(() => {}),
      )
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => {
    if (selected || !session) return;
    const frame = requestAnimationFrame(() =>
      document.getElementById(homeSection)?.scrollIntoView({ block: "start" }),
    );
    return () => cancelAnimationFrame(frame);
  }, [homeSection, selected, session?.organization_id]);
  function clearWorkspaceView() {
    viewEpoch.current += 1;
    setSelected(null);
    setWorkspaces([]);
    setWorkspaceCursor(null);
    setCreating(false);
    setHomeSection("workspaces");
  }
  async function login(body: unknown) {
    setError("");
    setAuthBusy(true);
    try {
      const response = await fetch("/api/session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await response.json();
      if (!response.ok)
        throw new Error(data.message || data.code || "Unable to sign in.");
      clearWorkspaceView();
      setSession(data.session);
      await load();
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setAuthBusy(false);
    }
  }
  async function logout() {
    setError("");
    try {
      const response = await fetch("/api/session", { method: "DELETE" });
      if (!response.ok)
        throw new Error(
          "Unable to revoke the session. Please try signing out again.",
        );
      setSession(null);
      clearWorkspaceView();
      const demo = await api<S["DemoIdentitiesResponse"]["result"]>(
        "auth/demo-identities",
      ).catch(() => null);
      setIdentities(demo?.users || []);
    } catch (error) {
      setError((error as Error).message);
    }
  }
  async function selectOrganization(id: string) {
    setError("");
    try {
      const updated = await api<S["Session"]>("auth/organization", {
        organization_id: id,
      });
      clearWorkspaceView();
      setSession(updated);
      await load();
    } catch (error) {
      setError((error as Error).message);
    }
  }
  const member = session?.memberships.find(
    (m) => m.organization_id === session.organization_id,
  );
  const canCreate = !!member?.roles.some(
    (role) => role === "owner" || role === "export_admin",
  );
  const demo =
    selected?.execution_scope === "demo" ||
    !!session?.user.id.startsWith("demo_");
  if (loading)
    return (
      <main className="loading">
        <Brand />
        <p role="status">Loading your export workspace…</p>
      </main>
    );
  return (
    <AppShell
      session={session}
      title={
        selected
          ? selected.product.description
          : homeSection === "usage"
            ? "Usage & plans"
            : homeSection === "team"
              ? "Team & access"
              : "Portfolio"
      }
      demo={demo}
      section={selected ? "workspaces" : homeSection}
      onNavigate={(section) => {
        setSelected(null);
        setHomeSection(section);
        setCreating(false);
      }}
      onLogout={logout}
      onOrganization={selectOrganization}
    >
      {error && (
        <div className="notice error" role="alert">
          {error}
        </div>
      )}
      {!session ? (
        <div className="auth-layout">
          <AuthIntroduction />
          <div className="auth-forms">
            <form
              className="card sign-in-card"
              onSubmit={(event) => {
                event.preventDefault();
                const form = new FormData(event.currentTarget);
                void login({
                  email: form.get("email"),
                  password: form.get("password"),
                });
              }}
            >
              <div className="eyebrow">WELCOME BACK</div>
              <h2>Sign in to your organization</h2>
              <p className="muted">
                Pick up where your last decision left off.
              </p>
              <label>
                Email
                <input
                  name="email"
                  type="email"
                  autoComplete="username"
                  required
                  placeholder="you@company.com"
                />
              </label>
              <label>
                Password
                <input
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  placeholder="Enter your password"
                />
              </label>
              <button disabled={authBusy}>
                {authBusy ? "Signing in…" : "Sign in"}
                <Icon name="arrow" size={17} />
              </button>
            </form>
            {identities.length > 0 && (
              <section className="card demo-entry">
                <div className="row">
                  <h2>Take a look around.</h2>
                  <span className="tag">Offline demo</span>
                </div>
                <p className="muted">
                  Try the full workflow with clearly labeled synthetic data.
                </p>
                <label>
                  Demo identity
                  <select id="identity">
                    {identities.map((identity) => (
                      <option key={identity.id} value={identity.id}>
                        {identity.display_name} · {identity.email}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  className="secondary"
                  disabled={authBusy}
                  onClick={() =>
                    login({
                      user_id: (
                        document.getElementById("identity") as HTMLSelectElement
                      ).value,
                    })
                  }
                >
                  Enter demo
                  <Icon name="arrow" size={16} />
                </button>
                <small>
                  Sample sources, financing, and results are illustrative.
                </small>
              </section>
            )}
          </div>
        </div>
      ) : selected ? (
        <Detail
          key={selected.id}
          workspace={selected}
          session={session}
          onBack={() => {
            setSelected(null);
            setHomeSection("workspaces");
            void load().catch((error) => setError(error.message));
          }}
          onWorkspace={(updated) =>
            setSelected((current) =>
              current?.id === updated.id ? updated : current,
            )
          }
        />
      ) : (
        <>
          <WorkspacePortfolio
            key={session.organization_id}
            workspaces={workspaces}
            onOpen={(workspace) => {
              setSelected(workspace);
              setHomeSection("workspaces");
            }}
            onNew={() => setCreating(!creating)}
            creating={creating}
            canCreate={canCreate}
            loading={listLoading}
          >
            {creating && (
              <Create
                onCreate={(workspace) => {
                  setCreating(false);
                  setSelected(workspace);
                  void load().catch((error) => setError(error.message));
                }}
              />
            )}
          </WorkspacePortfolio>
          {listLoading && (
            <p className="loading-inline" role="status">
              Loading workspaces…
            </p>
          )}
          {workspaceCursor && (
            <button
              className="secondary load-more"
              disabled={listLoading}
              onClick={() =>
                load(true).catch((error) => setError(error.message))
              }
            >
              Load more workspaces
            </button>
          )}
          <section id="usage" className="organization-section">
            <div className="section-heading">
              <div className="eyebrow">WORKSPACE RESOURCES</div>
              <h2>Usage & plans</h2>
              <p className="muted">
                Understand your allowance before starting new research.
              </p>
            </div>
            <Settings key={session.organization_id} />
          </section>
          {member?.roles.includes("owner") && (
            <section id="team" className="organization-section">
              <div className="section-heading">
                <div className="eyebrow">WORK BETTER TOGETHER</div>
                <h2>Team & access</h2>
                <p className="muted">
                  Keep responsibilities clear and access deliberate.
                </p>
              </div>
              <MemberAdmin
                key={session.organization_id}
                session={session}
                onChanged={async () => {
                  const updated = await api<S["Session"]>("auth/session");
                  setSession(updated);
                  if (updated.organization_id) await load();
                  else setWorkspaces([]);
                }}
              />
            </section>
          )}
        </>
      )}
      <footer className="foot">
        <span>
          fincathon<span className="brand-dot">.</span>{" "}
          <span className="footer-note">Evidence to decisions.</span>
        </span>
        <span>Workspace timezones apply · English</span>
      </footer>
    </AppShell>
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
      <h2>Start with your product</h2>
      <div className="grid">
        <Field name="description" label="Product & goods description" />
        <label>
          Business profile
          <select name="profile">
            <option value="reseller">Reseller</option>
            <option value="producer">Producer</option>
          </select>
        </label>
        <label>
          Mode
          <select name="mode">
            <option value="sandbox">Exploration / sandbox</option>
            <option value="deal">Deal</option>
          </select>
        </label>
        <Field
          name="origin"
          label="Seller domicile (ISO code, e.g. ID)"
          required={false}
        />
        <Field
          name="destination"
          label="Destination country (e.g. SG)"
          required={false}
        />
        <Field
          name="dispatch"
          label="Goods dispatch country (ISO, if known)"
          required={false}
        />
        <Field name="currency" label="Reporting currency" value="IDR" />
        <Field
          name="timezone"
          label="Owner timezone (IANA)"
          value="Asia/Jakarta"
        />
      </div>
      {error && <div role="alert">{error}</div>}
      <button>Create workspace</button>
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
    [archiveConfirmed, setArchiveConfirmed] = useState(false),
    [deal, setDeal] = useState<D | null>(null),
    [tab, setTab] = useState("Overview"),
    [draftKind, setDraftKind] = useState<S["ArtifactKind"]>("agreement"),
    [draftLanguage, setDraftLanguage] = useState("en"),
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
  const archived = w.archived || !!deal?.archived;
  const canArchive = roles.some((r) => r === "owner" || r === "export_admin");
  const editor = !archived && canArchive;
  const finance =
    !archived && roles.some((r) => r === "owner" || r === "finance_reviewer");
  useEffect(() => {
    setArchiveConfirmed(false);
  }, [archived]);
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
        throw new Error("Pagination did not advance. Refresh the workspace.");
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
    if ((deal?.archived || w.archived) && !path.endsWith("/archive")) {
      setError(
        "This workspace is archived. Reactivate it before changing records.",
      );
      return null;
    }
    if (processing && path !== "runs/" + job?.id + "/cancel") {
      setError(
        "Wait for the current job to finish before changing its inputs.",
      );
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
      setMessage("Saved.");
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
      setMessage("Job accepted; waiting for the worker.");
    }
  }
  const analysis = analyses.at(-1);
  const confirmed = evidence.filter((e) => e.review_status === "confirmed");
  if (!loaded)
    return (
      <>
        <button className="link" onClick={onBack}>
          ← All workspaces
        </button>
        <p role="status">{error || "Loading workspace context…"}</p>
      </>
    );
  return (
    <>
      <button className="link" onClick={onBack}>
        ← All workspaces
      </button>
      <div className="row workspace-heading">
        <div>
          <div className="eyebrow">
            {w.business_profile === "producer" ? "Producer" : "Reseller"} ·{" "}
            {w.seller_domicile} → {w.destination_country}
          </div>
          <h1>{w.product.description}</h1>
          <p className="muted">
            {deal ? "Deal" : "Exploration"} · {w.reporting_currency} · revision{" "}
            {revision}
          </p>
        </div>
        <span className={"tag " + (w.execution_scope === "demo" ? "demo" : "")}>
          {w.execution_scope === "demo"
            ? "DEMO · ALL DATA IS SYNTHETIC"
            : "ORGANIZATION WORKSPACE"}
        </span>
      </div>
      {deal && (
        <>
          <div className="state-summary" aria-label="Current deal status">
            {(
              [
                "execution_gate",
                "goods",
                "buyer_payment",
                "internal_closure",
              ] as const
            ).map((key) => (
              <div key={key}>
                <small>{title(key)}</small>
                <strong>{title(deal.states[key])}</strong>
              </div>
            ))}
          </div>
          <details className="state-details">
            <summary>All status dimensions</summary>
            <div className="actions">
              {Object.entries(deal.states).map(([key, value]) => (
                <span key={key} className="status">
                  {title(key)}: {title(value)}
                </span>
              ))}
            </div>
          </details>
        </>
      )}
      {(w.archived || deal?.archived) && (
        <p className="notice" role="status">
          This workspace is archived. Evidence, history, and exports remain
          available.
        </p>
      )}
      <nav className="tabs" aria-label="Workspace sections">
        {[
          "Overview",
          "Evidence & documents",
          "Economics & cash",
          "Scenarios & funding",
          "Drafts & approvals",
          "Readiness & timeline",
          "Settlement & closure",
          "History",
        ].map((t, index) => (
          <button
            className={tab === t ? "active" : ""}
            key={t}
            aria-label={t}
            aria-current={tab === t ? "page" : undefined}
            onClick={() => setTab(t)}
          >
            <span className="tab-number" aria-hidden="true">
              {String(index + 1).padStart(2, "0")}
            </span>
            {t}
          </button>
        ))}
      </nav>
      {tab === "Overview" && !archived && (
        <section className="context-note" aria-label="Workspace guide">
          <div>
            <strong>
              {!deal
                ? "Start with a question. Shape it with evidence."
                : analysis?.current_for_use === false
                  ? "Your inputs have changed."
                  : analysis
                    ? "Understand the trade-offs before moving forward."
                    : "Build your first financial picture."}
            </strong>
            <p>
              {!deal
                ? "Set your planning assumptions below, or add source evidence as it becomes available. You can explore before a buyer or quotation is confirmed."
                : analysis?.current_for_use === false
                  ? "Refresh the analysis and review its sources before using an earlier approval or draft."
                  : analysis
                    ? "Review cash timing, remaining gaps, and the evidence behind each result. A completed analysis does not establish transaction readiness."
                    : "Review your product, costs, and payment dates, then run a traceable analysis."}
            </p>
          </div>
          <button
            className="link"
            onClick={() =>
              setTab(
                analysis && analysis.current_for_use !== false
                  ? "Economics & cash"
                  : "Evidence & documents",
              )
            }
          >
            {analysis && analysis.current_for_use !== false
              ? "Explore the economics"
              : "Review evidence"}
            <Icon name="arrow" size={16} />
          </button>
        </section>
      )}
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
          Job {title(job.status)} <code>{job.id}</code>
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
              Cancel
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
                Retry with the latest revision
              </button>
            )}
          <Issues items={[...(job.blockers || []), ...(job.warnings || [])]} />
          {!!job.provider_receipts?.length && (
            <details>
              <summary>Source & provider access trail</summary>
              {job.provider_receipts.map((receipt, index) => (
                <p key={index}>
                  {receipt.provider} · {receipt.status} ·{" "}
                  {receipt.data_mode || "no data"}
                  <br />
                  {receipt.fetched_at} ·{" "}
                  {receipt.request_id || "Provider ID unavailable"}
                  <br />
                  {receipt.limitations.join(" · ")}
                  {receipt.retry_after !== null && (
                    <> · Provider retry window: {receipt.retry_after} seconds</>
                  )}
                  {receipt.source_url && (
                    <>
                      <br />
                      <a
                        href={receipt.source_url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open original source
                      </a>
                    </>
                  )}
                </p>
              ))}
            </details>
          )}
        </section>
      )}
      {tab === "Overview" && (
        <>
          <div className="split">
            <section className="card">
              <h2>Product facts</h2>
              <p>{w.product.description}</p>
              <p className="muted">
                {w.dispatch_country} → {w.destination_country}
                <br />
                Owner timezone: {w.owner_timezone}
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
                            reason: "Product description updated by owner",
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
                    label="Product description"
                    value={w.product.description}
                  />
                  <button disabled={busy || processing}>Save changes</button>
                </form>
              )}
            </section>
            <section className="card">
              <h2>Latest analysis</h2>
              {analysis ? (
                <>
                  <span className="tag">{title(analysis.completeness)}</span>
                  {analysis.current_for_use === false && (
                    <span className="status">
                      Inputs changed / source expired
                    </span>
                  )}
                  <p>
                    Contribution:{" "}
                    <strong>
                      {money(analysis.after_financing.contribution)}
                    </strong>
                  </p>
                  <p className="muted">
                    {date(analysis.created_at)}
                    <br />
                    Completeness applies to the declared inputs.
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
                  Add planning assumptions, then run a calculation through the
                  worker.
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
                  Recalculate analysis
                </button>
              )}
            </section>
          </div>
          {!deal && editor && (
            <>
              <Planning w={w} command={command} evidence={confirmed} />
              {w.planning_inputs && (
                <section className="card">
                  <h2>Move to a deal</h2>
                  <p className="muted">
                    Planning inputs remain as source records. Identities,
                    schedules, and prices still require evidence and
                    relevant-party agreement.
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
                    Create a deal from these inputs
                  </button>
                </section>
              )}
            </>
          )}
          {deal && (
            <section className="card">
              <h2>Deal structure</h2>
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
                {deal.line_items.length} goods lines · {deal.shipments.length}{" "}
                shipments · {deal.invoices.length} invoices
              </p>
            </section>
          )}
        </>
      )}
      {tab === "Evidence & documents" && (
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
            <h2>Original documents</h2>
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
                  Upload TXT, PDF, PNG, or JPEG (max. 10 MiB)
                  <input
                    name="files"
                    type="file"
                    accept=".txt,.pdf,.png,.jpg,.jpeg"
                    required
                  />
                </label>
                <button disabled={busy || processing}>
                  Upload & extract candidates
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
                      Retry extraction
                    </button>
                  )}
              </p>
            ))}
          </section>
          <section className="card">
            <h2>Fact candidates</h2>
            <p className="muted">
              Extracted facts still require review. Confirming a source does not
              automatically change deal values.
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
                              reason: "Reviewed through the workspace",
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
            <h2>Sources & excerpts</h2>
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
                <p>Location: {s.locator}</p>
                <p>
                  Effective from {s.effective_from || "not confirmed"} · until{" "}
                  {s.valid_until || "not confirmed"}
                </p>
                <p>
                  Source jurisdictions:{" "}
                  {s.applicability.jurisdictions.join(", ") || "needs review"} ·{" "}
                  {s.applicability.validity_reason}
                </p>
                {s.canonical_url && (
                  <a href={s.canonical_url} rel="noreferrer" target="_blank">
                    Public source ↗
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
                        reason: "Source reviewed for this deal",
                      })
                    }
                  >
                    Confirm source
                  </button>
                )}
              </details>
            ))}
          </section>
        </>
      )}
      {tab === "Economics & cash" && (
        <>
          <section className="card">
            <h2>Declared costs</h2>
            <div className="scroll">
              <table>
                <thead>
                  <tr>
                    <th>Component / treatment</th>
                    <th>Estimate</th>
                    <th>Actual</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {costs.map((c) => (
                    <tr key={c.id}>
                      <td>
                        {componentTitle(c.component_key, deal)}
                        <br />
                        <small>
                          {title(c.treatment)} · {title(c.status)} · Coverage:{" "}
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
                              setTab("Evidence & documents");
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
                <h2>Contribution & cash needs</h2>
                <div className="grid">
                  <Metric
                    label="Contribution after financing"
                    value={money(analysis.after_financing.contribution)}
                  />
                  <Metric
                    label="Minimum cash"
                    value={analysis.cash_metrics?.minimum_cash}
                  />
                  <Metric
                    label="Buffer shortfall"
                    value={analysis.cash_metrics?.buffer_shortfall}
                  />
                  <Metric
                    label="Closing cash"
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
                <h3>Server-calculated cash sequence</h3>
                <div className="scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>Direction</th>
                        <th>Quantity</th>
                        <th>Balance after event</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analysis.cash_metrics?.event_balances?.map((p, n) => (
                        <tr key={n}>
                          <td>{date(p.at)}</td>
                          <td>
                            {p.direction === "in" ? "Sign in" : "Sign out"}
                          </td>
                          <td>{money(p.amount)}</td>
                          <td>{money(p.balance)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <h3>Negative cash intervals</h3>
                {analysis.cash_metrics?.negative_intervals.map((i, n) => (
                  <p key={n}>
                    {date(i.start)} →{" "}
                    {i.end
                      ? date(i.end)
                      : "Still open at the end of the horizon"}
                  </p>
                ))}
                <h3>Pricing & comparables</h3>
                <div className="grid">
                  <Metric
                    label="Seller floor per unit"
                    value={analysis.price_range.seller_floor || undefined}
                  />
                  <Metric
                    label="Low market comparable"
                    value={analysis.price_range.market_low || undefined}
                  />
                  <Metric
                    label="High market comparable"
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
                    Excluded comparable: {c.reason}
                  </p>
                ))}
                <p className="muted">
                  {title(analysis.price_range.label)} · Noncomparable
                  observations do not become transaction prices.
                </p>
                <Lineage analysis={analysis} />
                <code>
                  Analysis {analysis.snapshot_hash} ·{" "}
                  {analysis.calculator_version}
                </code>
              </section>
            </>
          )}
        </>
      )}
      {tab === "Scenarios & funding" && (
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
            <h2>Financing: preparation only</h2>
            <p className="muted">
              Hypothetical offers do not prove fund availability, lender
              eligibility, or disbursement.
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
                Find funding options
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
                          : "Relative to an event"}
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
                    Calculate this funding scenario
                  </button>
                )}
              </article>
            ))}
          </section>
          <section className="card">
            <h2>Scenario comparison</h2>
            {analyses.map((a) => (
              <p key={a.id}>
                <code>{a.scenario_id}</code>
                <br />
                {money(a.after_financing.contribution)} · minimum cash{" "}
                {a.cash_metrics?.minimum_cash} · {title(a.completeness)}
                {a.owner_comparison && (
                  <>
                    <br />
                    Relative rank: {a.owner_comparison.rank ||
                      "not available"}{" "}
                    · preference{" "}
                    {a.owner_comparison.ranking_preference || "not selected"}
                    <br />
                    {a.owner_comparison.checks.map((check) => (
                      <span className="tag" key={check.code}>
                        {check.code}: {title(check.status)}
                      </span>
                    ))}
                    <br />
                    Parties whose acceptance is required:{" "}
                    {a.owner_comparison.required_counterparty_ids
                      .map(
                        (id) =>
                          deal?.parties.find((p) => p.id === id)
                            ?.display_name || id,
                      )
                      .join(", ") ||
                      "according to applicable contractual acceptance"}
                    <br />
                    <small>{a.owner_comparison.basis}</small>
                  </>
                )}
              </p>
            ))}
          </section>
        </>
      )}
      {tab === "Drafts & approvals" && (
        <>
          <section className="card">
            <h2>Commercial drafts</h2>
            <p className="muted">
              Download and review drafts. Complete all placeholders before using
              them.
            </p>
            {deal && analysis && editor && (
              <>
                <label>
                  Draft type
                  <select
                    value={draftKind}
                    onChange={(event) =>
                      setDraftKind(event.target.value as S["ArtifactKind"])
                    }
                  >
                    <option value="agreement">Agreement</option>
                    <option value="message">Counterparty message</option>
                    <option value="recommendation">
                      Internal recommendation
                    </option>
                    <option value="clause_revision">Proposed clause</option>
                    <option value="amendment">
                      Proposed agreement amendment
                    </option>
                  </select>
                </label>
                <label>
                  Draft language
                  <select
                    value={draftLanguage}
                    onChange={(event) => setDraftLanguage(event.target.value)}
                  >
                    <option value="id">Indonesian</option>
                    <option value="en">English</option>
                  </select>
                </label>
                <label>
                  Draft recipient
                  <select
                    value={draftRecipient}
                    onChange={(event) => setDraftRecipient(event.target.value)}
                  >
                    <option value="">Based on draft context</option>
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
                  Create a draft from analysis
                </button>
              </>
            )}
            {artifacts.map((a) => (
              <details key={a.id}>
                <summary>
                  {title(a.kind)} · {title(a.state)}
                </summary>
                <div className="source">{a.content}</div>
                <p>Placeholders: {a.placeholders.join(", ")}</p>
                <code>{a.content_hash}</code>
                <p>
                  <a
                    href={
                      "/api/gateway/" + root + "/artifacts/" + a.id + "/content"
                    }
                  >
                    Download draft
                  </a>
                </p>
              </details>
            ))}
          </section>
          {deal && analysis && roles.includes("owner") && (
            <section className="card">
              <h2>Owner review</h2>
              <p className="muted">
                Applies to the current analysis and evidence hashes. It does not
                replace counterparty acceptance or funds verification.
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
                Record plan approval
              </button>
            </section>
          )}
        </>
      )}
      {tab === "Readiness & timeline" && (
        <>
          <section className="card">
            <h2>Shipment readiness gate</h2>
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
                          <summary>Evidence: {source.title}</summary>
                          <p>
                            {source.publisher} · {title(source.mode)} ·{" "}
                            {title(source.review_status)} · {source.locator}
                          </p>
                          <blockquote>{source.claim}</blockquote>
                          <p>
                            Valid until: {source.valid_until || "Not stated"}
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
                              Download original source
                            </a>
                          )}
                        </details>
                      ) : (
                        <p key={ref.id}>
                          Source {ref.id} · see authorized history
                        </p>
                      );
                    })}
                  </div>
                ))}
              </>
            ) : (
              <p className="muted">Available after conversion to a deal.</p>
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
            <h2>Requirements</h2>
            {requirements.map((r) => (
              <article key={r.id}>
                <h3>{r.category}</h3>
                <p>
                  {title(r.applicability)} · {title(r.fulfillment_status)}
                </p>
                <p className="muted">
                  {r.evidence_ids.length} sources ·{" "}
                  {r.fulfillment_evidence_ids.length} fulfillment evidence
                </p>
              </article>
            ))}
          </section>
          <section className="card">
            <h2>Internal timeline</h2>
            <div className="timeline">
              {milestones.map((m) => (
                <article key={m.id}>
                  <strong>{title(m.kind)}</strong>
                  <p>
                    {m.schedule.kind === "fixed"
                      ? "Fixed date"
                      : "Relative to " + m.schedule.anchor_milestone_id}
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
                  {m.actual && <span className="tag">Verified actual</span>}
                </article>
              ))}
            </div>
            {milestones.length === 0 && (
              <p className="muted">
                No milestones recorded yet. Payment dates appear on their
                respective obligations.
              </p>
            )}
          </section>
        </>
      )}
      {tab === "Settlement & closure" && (
        <>
          <section className="card">
            <h2>Obligations & payment evidence</h2>
            <p className="muted">
              Buyer payment and internal closure are separate states. Pending
              evidence does not settle an obligation.
            </p>
            <div className="scroll">
              <table>
                <thead>
                  <tr>
                    <th>Obligation</th>
                    <th>Quantity</th>
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
                {r.supersedes && <small>Supersedes {r.supersedes}</small>}
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
              <h2>Internal reconciliation</h2>
              {reconciliations.map((r) => (
                <details key={r.id}>
                  <summary>
                    {date(r.created_at)} · {title(r.closure_gate.status)}
                  </summary>
                  <p>Actual contribution: {money(r.actual_contribution)}</p>
                  <p>
                    {r.unresolved_obligation_ids.length} unresolved obligations
                  </p>
                  <Issues items={r.unresolved_disputes} />
                  {r.dimensions?.map((row, n) => (
                    <p key={n}>
                      {title(row.category)} · {title(row.baseline_kind)} ·{" "}
                      {row.baseline_value ?? "Not yet known"} →{" "}
                      {row.actual_value ?? "Not yet known"} {row.unit}
                      <br />
                      <small>{row.basis}</small>
                    </p>
                  ))}
                  <div className="scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Component</th>
                          <th>Baseline</th>
                          <th>Actual</th>
                          <th>Variance</th>
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
                          ? "Closure is still blocked. Review the gate conditions."
                          : "The deal is closed after all prerequisites have been met.",
                      );
                    }
                  }}
                >
                  Evaluate internal closure
                </button>
              )}

              <p className="muted">
                Compare actuals with the retained baseline. Closure remains
                blocked while prerequisites are unmet.
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
                Run reconciliation
              </button>
            </section>
          )}
        </>
      )}
      {deal && editor && tab === "Overview" && (
        <fieldset disabled={busy || processing}>
          <PartyEntry deal={deal} evidence={confirmed} command={command} />
          <OwnerEntry deal={deal} evidence={confirmed} command={command} />
        </fieldset>
      )}
      {deal &&
        !archived &&
        roles.some(
          (role) => role === "owner" || role === "production_procurement",
        ) &&
        tab === "Readiness & timeline" && (
          <fieldset disabled={busy || processing}>
            <RuleEntry deal={deal} evidence={confirmed} command={command} />
          </fieldset>
        )}
      {deal && finance && tab === "Scenarios & funding" && (
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
        (tab === "Economics & cash" ||
          (finance && tab === "Settlement & closure")) && (
          <fieldset disabled={busy || processing}>
            <FinancialEntry
              deal={deal}
              evidence={confirmed}
              obligations={obligations}
              costs={costs}
              fx={fx}
              finance={finance && tab === "Settlement & closure"}
              showCosts={tab === "Economics & cash"}
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
            !archived &&
            (roles.includes("owner") ||
              roles.includes("production_procurement"))
          }
        />
      )}
      {tab === "History" && (
        <>
          <HistoryPanel workspace={w} deal={deal} read={api} date={date} />
          {canArchive && (
            <section className="card">
              <h2>
                {w.archived ? "Reactivate workspace" : "Archive workspace"}
              </h2>
              <p>
                Archival pauses changes to this workspace and its linked deal.
                Evidence, original files, and history are retained. Reactivation
                follows the current plan limits.
              </p>
              <label>
                <input
                  type="checkbox"
                  checked={archiveConfirmed}
                  onChange={(event) =>
                    setArchiveConfirmed(event.target.checked)
                  }
                />{" "}
                I have reviewed this {w.archived ? "reactivation" : "archival"}{" "}
                action.
              </label>
              <button
                className="secondary"
                disabled={!archiveConfirmed || busy || processing}
                onClick={async () => {
                  const result = await command(root + "/archive", {
                    expected_revision: revision,
                    archived: !w.archived,
                  });
                  if (result) setArchiveConfirmed(false);
                }}
              >
                {w.archived ? "Reactivate" : "Archive workspace"}
              </button>
            </section>
          )}
        </>
      )}
    </>
  );
}
function Metric({ label, value }: { label: string; value?: string }) {
  return (
    <div className="metric">
      <small>{label}</small>
      <strong>{value || "Not yet known"}</strong>
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
            "Complete the balance, commitments, buffer, and balance time together. Blank amounts are not treated as zero.",
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
      <h2>Initial planning assumptions</h2>
      <p className="muted">
        All values are in {w.reporting_currency}. Missing inputs remain unknown.
        Scenario times use {w.owner_timezone}; no time is assumed from a date
        alone.
      </p>
      <div className="grid">
        <Field name="quantity" label="Quantity" value="10" />
        <Field name="unit" label="Unit" value="kg" />
        <Field name="cash" label="Available opening balance" required={false} />
        <Field
          name="committed"
          label="Funds committed outside this deal"
          required={false}
        />
        <Field name="buffer" label="Your minimum buffer" required={false} />
        <Field
          name="cash_date"
          label="Balance time in owner's timezone"
          type="datetime-local"
          required={false}
        />
        <Field
          name="margin"
          label="Target contribution margin (%)"
          required={false}
        />
        <Field name="cost" label="Cost per unit" required={false} />
        <Field name="invoice" label="Total buyer invoice" required={false} />
        <Field name="deposit" label="Buyer deposit" required={false} />
        <Field
          name="deposit_at"
          label="Deposit scenario time"
          type="datetime-local"
          required={false}
        />
        <Field
          name="balance_at"
          label="Buyer balance scenario time"
          type="datetime-local"
          required={false}
        />
        <Field
          name="cost_at"
          label="Input payment scenario time"
          type="datetime-local"
          required={false}
        />
      </div>
      <label>
        Sources supporting these assumptions
        <select name="evidence" multiple>
          {evidence.map((source) => (
            <option key={source.id} value={source.id}>
              {source.title}
            </option>
          ))}
        </select>
      </label>
      {error && <p role="alert">{error}</p>}
      <button>Save planning assumptions</button>
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
      <summary>Record pending payment evidence</summary>
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
          Obligation
          <select name="obligation">
            {obligations.map((o) => (
              <option value={o.id} key={o.id}>
                {o.id} · {money(o.amount)}
              </option>
            ))}
          </select>
        </label>
        <Field name="amount" label="Amount received" />
        <Field name="date" label="Value date" type="date" />
        <label>
          Reviewed evidence
          <select name="evidence" required>
            {evidence.map((e) => (
              <option key={e.id} value={e.id}>
                {e.title}
              </option>
            ))}
          </select>
        </label>
        <button disabled={!evidence.length}>Save pending evidence</button>
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
      <summary>Usage & plans · {data.plan}</summary>
      <p>{title(data.status)}</p>
      <p>
        Active deal slots: {data.active_deals} / {data.active_deal_limit} ·
        member limit {data.user_limit}
      </p>
      {data.allowances.map((a) => (
        <p key={a.unit}>
          {title(a.unit)}: {a.included_remaining} remaining · add-on{" "}
          {a.addon_remaining} · valid until{" "}
          {a.expires_at || "according to the plan period"}
        </p>
      ))}
      <p className="muted">
        Deterministic calculations and manual payment records do not consume
        enriched research allowance.
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
      <summary>Trace formulas & source revisions</summary>
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
                Source revision {ref.revision} · {ref.id.slice(-8)}
              </button>
            ))}
          </div>
          <p className="muted">
            {line.input_refs.length} fixed-version inputs; later changes do not
            overwrite this analysis.
          </p>
        </article>
      ))}
      {!analysis.numeric_lineage && (
        <p className="muted">
          Recalculate to obtain source revision references.
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
      <summary>Organization members & permissions</summary>
      <p>
        Use a local account ID provisioned by your operator. Clearing all roles
        revokes membership. The organization must retain an owner.
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
            setMessage("Member permissions updated.");
          } catch (error) {
            setError((error as Error).message);
          }
        }}
      >
        <Field name="user" label="Member account ID" />
        <fieldset>
          <legend>Assigned roles</legend>
          {roles.map((role) => (
            <label key={role}>
              <input type="checkbox" name="roles" value={role} />
              {title(role)}
            </label>
          ))}
        </fieldset>
        <button>Save member permissions</button>
      </form>
    </details>
  );
}
