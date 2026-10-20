"use client";
import { useEffect, useState } from "react";
import type { components } from "../../../../packages/contracts/api";
type S = components["schemas"];
type Command = (
  path: string,
  body: unknown,
  method?: string,
) => Promise<unknown>;
export function CalendarPanel({
  deal,
  milestones,
  demo,
  disabled,
  command,
  run,
}: {
  deal: S["Deal"];
  milestones: S["Milestone"][];
  demo: boolean;
  disabled: boolean;
  command: Command;
  run: (path: string, body: unknown) => Promise<void>;
}) {
  const [connections, setConnections] = useState<S["CalendarConnection"][]>([]),
    [connection, setConnection] = useState(""),
    [selected, setSelected] = useState<string[]>([]),
    [action, setAction] = useState<"insert" | "update" | "delete">("insert"),
    [preview, setPreview] = useState<S["CalendarPreview"] | null>(null),
    [approved, setApproved] = useState(false),
    [syncReady, setSyncReady] = useState(demo),
    [calendarId, setCalendarId] = useState("primary"),
    [error, setError] = useState("");
  const root = "deals/" + deal.id;
  async function refresh() {
    const response = await fetch("/api/gateway/calendar/connections");
    const body = await response.json();
    if (!response.ok)
      throw new Error(body.message || "Unable to load connections.");
    setConnections(body.result.items);
    const matching = body.result.items.filter(
      (c: S["CalendarConnection"]) =>
        c.data_mode === (demo ? "synthetic_demo" : "live") &&
        c.status === "connected",
    );
    setConnection((current) => current || (!demo && matching.at(-1)?.id) || "");
    const capabilities = await fetch("/api/gateway/capabilities", {
      cache: "no-store",
    });
    if (!capabilities.ok)
      throw new Error("Unable to check calendar availability.");
    const capabilityBody = await capabilities.json();
    setSyncReady(
      capabilityBody.result.items.some(
        (c: S["Capability"]) => c.name === "calendar" && c.state === "ready",
      ),
    );
  }
  useEffect(() => {
    refresh().catch((error) => setError(error.message));
  }, []);
  function invalidate() {
    setPreview(null);
    setApproved(false);
  }
  async function connect() {
    setError("");
    const auth = (await command("calendar/connections", {
      redirect_uri: location.origin + "/oauth/calendar/callback",
    })) as S["CalendarAuthorization"] | null;
    if (!auth) return;
    if (!demo) {
      window.location.assign(auth.authorization_url);
      return;
    }
    const connected = (await command("calendar/callback", {
      state: auth.state,
      code: "offline-demo",
    })) as S["CalendarConnection"] | null;
    if (!connected) return;
    await command("calendar/connections/" + connected.id + "/selection", {
      calendar_id: "synthetic-local",
    });
    setConnection(connected.id);
    invalidate();
    await refresh();
  }
  const active = connections.find((c) => c.id === connection);
  return (
    <details className="card">
      <summary>External calendar sync (optional)</summary>
      <p>
        Your internal timeline works independently of external calendars.
        Projections include only selected milestone titles and dates, without
        attendees, contract values, or party identities.
      </p>
      {!demo ? (
        <p>
          Connect your Google account and select a calendar.{" "}
          {syncReady
            ? "An operator has enabled live sync. Each projection still requires your approval."
            : "Live projections remain disabled until account validation is recorded and an operator enables them."}
        </p>
      ) : (
        <strong>SYNTHETIC DEMO · no Google requests</strong>
      )}
      <>
        {error && <p role="alert">{error}</p>}
        <div className="actions">
          <button
            disabled={disabled}
            onClick={() => connect().catch((error) => setError(error.message))}
          >
            {demo ? "Connect demo calendar" : "Connect Google Calendar"}
          </button>
          <button
            className="secondary"
            disabled={disabled}
            onClick={() => refresh().catch((error) => setError(error.message))}
          >
            Refresh projection status
          </button>
        </div>
        <label>
          Calendar connection
          <select
            value={connection}
            onChange={(e) => {
              setConnection(e.target.value);
              invalidate();
            }}
          >
            <option value="">Select a connection</option>
            {connections
              .filter((c) => c.data_mode === (demo ? "synthetic_demo" : "live"))
              .map((c) => (
                <option key={c.id} value={c.id}>
                  {c.calendar_id || c.id} · {c.status}
                </option>
              ))}
          </select>
        </label>
        {active && (
          <>
            <p>
              Connection status: {active.status} · {active.data_mode}
            </p>
            {!demo && active.status === "connected" && (
              <form
                onSubmit={async (event) => {
                  event.preventDefault();
                  const result = await command(
                    "calendar/connections/" + active.id + "/selection",
                    { calendar_id: calendarId.trim() },
                  );
                  if (result) {
                    invalidate();
                    await refresh();
                  }
                }}
              >
                <label>
                  Google calendar ID
                  <input
                    value={calendarId}
                    onChange={(event) => setCalendarId(event.target.value)}
                    required
                  />
                </label>
                <p>
                  Use primary for your account's main calendar, or the ID of a
                  calendar you own. Selecting a calendar does not send events.
                </p>
                <button disabled={disabled || !calendarId.trim()} type="submit">
                  Select Google calendar
                </button>
              </form>
            )}
            {active.status === "connected" && (
              <button
                disabled={disabled}
                className="secondary"
                onClick={async () => {
                  await command(
                    "calendar/connections/" + active.id + "/revoke",
                    {},
                  );
                  invalidate();
                  await refresh();
                }}
              >
                Revoke this connection
              </button>
            )}
            {active.owned_events?.map((event) => (
              <div key={event.milestone_id}>
                <p>
                  {event.milestone_id} · projection status: {event.state}
                </p>
                {event.state === "conflict" && (
                  <div className="actions">
                    {(["keep_external", "reapprove_projection"] as const).map(
                      (decision) => (
                        <button
                          key={decision}
                          disabled={disabled}
                          onClick={async () => {
                            await command(root + "/calendar-conflicts", {
                              expected_revision: deal.revision,
                              connection_id: active.id,
                              milestone_id: event.milestone_id,
                              decision,
                            });
                            invalidate();
                            await refresh();
                          }}
                        >
                          {decision === "keep_external"
                            ? "Keep external changes"
                            : "Review projection again"}
                        </button>
                      ),
                    )}
                  </div>
                )}
              </div>
            ))}
          </>
        )}
        <fieldset disabled={disabled || active?.status !== "connected"}>
          <legend>Milestones to project</legend>
          {milestones.map((m) => (
            <label key={m.id}>
              <input
                type="checkbox"
                checked={selected.includes(m.id)}
                onChange={(e) => {
                  setSelected((ids) =>
                    e.target.checked
                      ? [...ids, m.id]
                      : ids.filter((id) => id !== m.id),
                  );
                  invalidate();
                }}
              />
              {m.kind} · {m.id}
            </label>
          ))}
        </fieldset>
        <label>
          Projection action
          <select
            value={action}
            onChange={(e) => {
              setAction(e.target.value as typeof action);
              invalidate();
            }}
          >
            <option value="insert">Insert</option>
            <option value="update">Update app-owned events</option>
            <option value="delete">Delete app-owned events</option>
          </select>
        </label>
        <button
          disabled={
            disabled || !selected.length || active?.status !== "connected"
          }
          onClick={async () => {
            const value = (await command(root + "/calendar-preview", {
              expected_revision: deal.revision,
              connection_id: connection,
              milestone_ids: selected,
              action,
            })) as S["CalendarPreview"] | null;
            setPreview(value);
            setApproved(false);
          }}
        >
          Preview projection
        </button>
        {preview && (
          <>
            <p>
              Projection hash: <code>{preview.projection_hash}</code>
            </p>
            {preview.events.map((event) => (
              <p key={event.milestone_id}>
                {event.title} ·{" "}
                {"date" in event.date ? event.date.date : event.date.instant} ·{" "}
                {event.date.timezone} · {event.action}
              </p>
            ))}
            <button
              disabled={disabled || approved}
              onClick={async () => {
                const result = await command(root + "/approvals", {
                  expected_revision: deal.revision,
                  purpose: "calendar_write",
                  analysis_hash: preview.projection_hash,
                  artifact_hash: null,
                  evidence_digest: preview.projection_hash,
                  decision: "approved",
                });
                if (result) setApproved(true);
              }}
            >
              Approve this projection hash
            </button>
            <button
              disabled={disabled || !approved || !syncReady}
              onClick={() =>
                run(root + "/calendar-sync", {
                  expected_revision: deal.revision,
                  connection_id: connection,
                  approved_projection_hash: preview.projection_hash,
                  milestone_ids: selected,
                  action,
                })
              }
            >
              {demo
                ? "Run approved demo projection"
                : "Run approved Google projection"}
            </button>
            <p>
              An accepted job does not mean events have been delivered. Refresh
              the projection status to check the delivery result.
            </p>
          </>
        )}
      </>
    </details>
  );
}
