"use client";

import { useState, type ReactNode } from "react";
import type { components } from "../../../../packages/contracts/api";
import { Icon } from "./app-shell";

type Workspace = components["schemas"]["Workspace"];
export function WorkspacePortfolio({
  workspaces,
  onOpen,
  onNew,
  creating,
  canCreate,
  loading,
  children,
}: {
  workspaces: Workspace[];
  onOpen: (workspace: Workspace) => void;
  onNew: () => void;
  creating: boolean;
  canCreate: boolean;
  loading: boolean;
  children: ReactNode;
}) {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState("all");
  const visible = workspaces.filter(
    (workspace) =>
      (mode === "all" ||
        (mode === "deal"
          ? !!workspace.deal_id || workspace.mode === "deal"
          : workspace.mode === "sandbox" && !workspace.deal_id)) &&
      [
        workspace.product.description,
        workspace.seller_domicile,
        workspace.dispatch_country,
        workspace.destination_country,
        workspace.business_profile,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(query.trim().toLowerCase()),
  );
  const deals = workspaces.filter((w) => !!w.deal_id || w.mode === "deal");
  return (
    <>
      <section className="portfolio-heading" id="workspaces">
        <div>
          <div className="eyebrow">YOUR EXPORT PORTFOLIO</div>
          <h1>Your workspaces</h1>
          <p className="muted">
            A clear view of what you are exploring, planning, and moving
            forward.
          </p>
        </div>
        {canCreate && (
          <button
            onClick={onNew}
            className={creating ? "secondary" : ""}
            aria-expanded={creating}
          >
            {creating ? "Cancel new workspace" : "+ New workspace"}
          </button>
        )}
      </section>
      <section
        className="portfolio-summary"
        aria-label="Loaded workspace summary"
      >
        <div>
          <span className="summary-icon">
            <Icon name="grid" />
          </span>
          <div>
            <small>WORKSPACES LOADED</small>
            <strong>
              {workspaces.length}
              <span>in this view</span>
            </strong>
          </div>
        </div>
        <div>
          <span className="summary-icon">
            <Icon name="globe" />
          </span>
          <div>
            <small>EXPLORATIONS</small>
            <strong>
              {workspaces.length - deals.length}
              <span>questions taking shape</span>
            </strong>
          </div>
        </div>
        <div>
          <span className="summary-icon">
            <Icon name="box" />
          </span>
          <div>
            <small>DEALS</small>
            <strong>
              {deals.length}
              <span>with transaction context</span>
            </strong>
          </div>
        </div>
      </section>
      {children}
      <div className="portfolio-toolbar">
        <div className="portfolio-filters" aria-label="Workspace type filters">
          {[
            ["all", "All workspaces"],
            ["deal", "Deals"],
            ["sandbox", "Explorations"],
          ].map(([value, label]) => (
            <button
              key={value}
              aria-pressed={mode === value}
              onClick={() => setMode(value)}
            >
              {label}
            </button>
          ))}
        </div>
        <label className="workspace-search">
          <Icon name="search" size={17} />
          <span className="sr-only">Search loaded workspaces</span>
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search a product or route…"
          />
        </label>
      </div>
      <div className="portfolio-results" aria-live="polite">
        <span>
          {visible.length} {visible.length === 1 ? "workspace" : "workspaces"}{" "}
          in this view
        </span>
        <span>Product · Route · Business profile</span>
      </div>
      <div className="workspace-grid">
        {visible.map((workspace) => (
          <article className="workspace-card" key={workspace.id}>
            <div className="workspace-card-top">
              <span className="product-icon">
                <Icon name="box" size={23} />
              </span>
              <div className="workspace-badges">
                <span
                  className={
                    "tag " +
                    (workspace.deal_id || workspace.mode === "deal"
                      ? "deal-tag"
                      : "")
                  }
                >
                  {workspace.deal_id || workspace.mode === "deal"
                    ? "Deal"
                    : "Exploration"}
                </span>
                {workspace.archived && <span className="status">Archived</span>}
              </div>
            </div>
            <h2>{workspace.product.description}</h2>
            <p className="workspace-route">
              <span>{workspace.seller_domicile || "Origin not set"}</span>
              <span aria-hidden="true">→</span>
              <span>
                {workspace.destination_country || "Destination not set"}
              </span>
            </p>
            <div className="workspace-meta">
              <span>
                {workspace.business_profile === "producer"
                  ? "Producer"
                  : "Reseller"}
              </span>
              <span>{workspace.reporting_currency}</span>
              {workspace.execution_scope === "demo" && (
                <span className="demo-source">Synthetic demo</span>
              )}
            </div>
            <div className="workspace-card-bottom">
              <small>Revision {workspace.revision}</small>
              <button className="link" onClick={() => onOpen(workspace)}>
                Open workspace <Icon name="arrow" size={16} />
              </button>
            </div>
          </article>
        ))}
      </div>
      {loading && workspaces.length === 0 && (
        <p className="loading-inline" role="status">
          Loading your workspaces…
        </p>
      )}
      {!loading && visible.length === 0 && (
        <section className="empty-state">
          <span className="product-icon">
            <Icon name={query ? "search" : "grid"} size={26} />
          </span>
          <h2>
            {query || mode !== "all"
              ? "No matching workspaces"
              : "Your next export starts here."}
          </h2>
          <p>
            {query || mode !== "all"
              ? "Try another product, country code, or workspace type. Filters apply to the workspaces loaded so far."
              : "Start with a product and a destination. You can explore before you have a buyer or a document."}
          </p>
          {query || mode !== "all" ? (
            <button
              className="secondary"
              onClick={() => {
                setQuery("");
                setMode("all");
              }}
            >
              Clear filters
            </button>
          ) : (
            canCreate &&
            !creating && (
              <button onClick={onNew}>Create your first workspace</button>
            )
          )}
        </section>
      )}
    </>
  );
}
