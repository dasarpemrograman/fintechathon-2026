"use client";

import type { ReactNode } from "react";
import type { components } from "../../../../packages/contracts/api";

type Session = components["schemas"]["Session"];
export type HomeSection = "workspaces" | "usage" | "team";
export function Icon({
  name,
  size = 20,
}: {
  name:
    | "grid"
    | "arrow"
    | "search"
    | "box"
    | "chart"
    | "team"
    | "exit"
    | "globe"
    | "check";
  size?: number;
}) {
  const paths = {
    grid: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" />
      </>
    ),
    arrow: (
      <>
        <path d="M4 12h15M13 5l7 7-7 7" />
      </>
    ),
    search: (
      <>
        <circle cx="10.5" cy="10.5" r="6.5" />
        <path d="m16 16 5 5" />
      </>
    ),
    box: (
      <>
        <path d="m12 3 9 5-9 5-9-5 9-5Z M3 8v9l9 5 9-5V8 M12 13v9 M7.5 5.5l9 5" />
      </>
    ),
    chart: (
      <>
        <path d="M4 3v17h17M8 15v-4M13 15V7M18 15v-6" />
      </>
    ),
    team: (
      <>
        <circle cx="9" cy="8" r="3" />
        <path d="M3 21v-3a6 6 0 0 1 12 0v3M17 5a3 3 0 0 1 0 6M18 15a5 5 0 0 1 3 5" />
      </>
    ),
    exit: (
      <>
        <path d="M9 4H4v16h5M10 12h11M17 8l4 4-4 4" />
      </>
    ),
    globe: (
      <>
        <circle cx="12" cy="12" r="9" />
        <ellipse cx="12" cy="12" rx="4" ry="9" />
        <path d="M3 12h18" />
      </>
    ),
    check: (
      <>
        <path d="m5 12 4 4L19 6" />
      </>
    ),
  };
  return (
    <svg
      aria-hidden="true"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
    </svg>
  );
}
export function Brand() {
  return (
    <span className="brand">
      <span className="brand-mark" aria-hidden="true">
        <i />
        <i />
        <i />
        <i />
      </span>
      <span>
        fincathon<span className="brand-dot">.</span>
      </span>
    </span>
  );
}
export function AppShell({
  session,
  title,
  demo,
  section,
  onNavigate,
  onLogout,
  onOrganization,
  children,
}: {
  session: Session | null;
  title?: string;
  demo: boolean;
  section: HomeSection;
  onNavigate: (section: HomeSection) => void;
  onLogout: () => void;
  onOrganization: (id: string) => void;
  children: ReactNode;
}) {
  const member = session?.memberships.find(
    (m) => m.organization_id === session.organization_id,
  );
  const roles: Record<string, string> = {
    owner: "Owner",
    export_admin: "Export admin",
    finance_reviewer: "Finance reviewer",
    production_procurement: "Production & procurement",
  };
  return (
    <div className={session ? "app-layout" : "public-layout"}>
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      {session && (
        <aside className="sidebar" aria-label="Application sidebar">
          <button
            className="brand-button"
            onClick={() => onNavigate("workspaces")}
            aria-label="Fincathon workspaces"
          >
            <Brand />
          </button>
          <div className="sidebar-label">YOUR WORKSPACE</div>
          <nav aria-label="Main navigation" className="sidebar-nav">
            <button
              aria-current={section === "workspaces" ? "page" : undefined}
              onClick={() => onNavigate("workspaces")}
            >
              <Icon name="grid" />
              Workspaces
            </button>
            <button
              aria-current={section === "usage" ? "page" : undefined}
              onClick={() => onNavigate("usage")}
            >
              <Icon name="chart" />
              Usage & plans
            </button>
            {member?.roles.includes("owner") && (
              <button
                aria-current={section === "team" ? "page" : undefined}
                onClick={() => onNavigate("team")}
              >
                <Icon name="team" />
                Team & access
              </button>
            )}
          </nav>
          <div className="sidebar-note">
            <span className="sidebar-note-icon">
              <Icon name="globe" size={24} />
            </span>
            <strong>A clearer way forward.</strong>
            <p>Evidence, economics, and your next export decision.</p>
          </div>
          <div className="sidebar-account">
            <span className="avatar">
              {session.user.display_name.slice(0, 1).toUpperCase()}
            </span>
            <div>
              <strong>{session.user.display_name}</strong>
              <small>
                {member?.roles.map((role) => roles[role] || role).join(" · ")}
              </small>
            </div>
            <button
              className="signout-icon"
              onClick={onLogout}
              aria-label="Sign out"
              title="Sign out"
            >
              <Icon name="exit" size={18} />
            </button>
          </div>
        </aside>
      )}
      <div className="app-body">
        <header className="topbar">
          {session ? (
            <>
              <div className="breadcrumb">
                <Icon name="grid" size={16} />
                <span>Workspace</span>
                <span aria-hidden="true">/</span>
                <strong>{title || "Portfolio"}</strong>
              </div>
              <div className="topbar-controls">
                <span className="locale-label">EN</span>
                <label className="organization-control">
                  <span className="sr-only">Organization</span>
                  <select
                    value={session.organization_id || ""}
                    onChange={(event) => onOrganization(event.target.value)}
                  >
                    <option value="" disabled>
                      Select an organization
                    </option>
                    {session.memberships.map((m) => (
                      <option key={m.id} value={m.organization_id}>
                        {m.organization_name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </>
          ) : (
            <>
              <Brand />
              <span className="topbar-caption">
                A thoughtful workspace for global trade.
              </span>
              <span className="locale-label">English · EN</span>
            </>
          )}
        </header>
        {demo && (
          <div className="demo-banner" role="note">
            <span className="demo-dot" aria-hidden="true" />
            <strong>Synthetic demo</strong>
            <span>Explore with sample data. Results are illustrative.</span>
          </div>
        )}
        <main id="main-content" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  );
}
export function AuthIntroduction() {
  return (
    <section className="auth-introduction">
      <div className="eyebrow">A CLEARER WAY TO EXPORT</div>
      <h1>
        Clarity for every
        <br />
        export decision<span>.</span>
      </h1>
      <p className="auth-description">
        Bring your evidence, economics, and next steps into focus. One
        workspace, from the first question to the final review.
      </p>
      <div className="auth-flow" aria-label="Your export decision workflow">
        {[
          [
            "01",
            "Build your evidence",
            "Know what is confirmed. See what is missing.",
          ],
          [
            "02",
            "Understand the economics",
            "Compare costs, cash timing, and alternatives.",
          ],
          [
            "03",
            "Prepare your next step",
            "Review terms, readiness, and verified actuals.",
          ],
        ].map(([number, title, description]) => (
          <div key={number}>
            <span className="auth-step">{number}</span>
            <div>
              <strong>{title}</strong>
              <p>{description}</p>
            </div>
          </div>
        ))}
      </div>
      <div className="auth-footnote">
        <Icon name="check" size={16} />
        <span>Your evidence stays traceable. Every decision stays yours.</span>
      </div>
    </section>
  );
}
