"use client";

import { useState } from "react";
import type { components } from "../../../../packages/contracts/api";

type S = components["schemas"];
type Temporal = S["TemporalValue"];
type CalendarEvent = {
  id: string;
  title: string;
  date: string | null;
  detail: string;
  status: string;
  dateStatus?: string;
  category: "milestone" | "payment" | "financing";
  amount?: string;
  balance?: string;
  direction?: "in" | "out";
  source: string;
  counterparty?: string;
};

function localDate(value: Temporal, timezone: string) {
  if ("date" in value) return value.date;
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: timezone,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(new Date(value.instant));
  const part = (type: string) => parts.find((item) => item.type === type)?.value || "";
  return `${part("year")}-${part("month")}-${part("day")}`;
}

function eventFor(milestone: S["Milestone"], timezone: string): CalendarEvent {
  const candidates: [Temporal | null | undefined, string][] = [
    [milestone.actual, "Verified actual"],
    [milestone.agreed, "Agreed date"],
    [milestone.resolved_forecast, "Forecast"],
    [milestone.forecast, "Forecast"],
    [milestone.proposed, "Proposed date"],
    [milestone.schedule.kind === "fixed" ? milestone.schedule.due : null, "Planned date"],
  ];
  const selected = candidates.find(([candidate]) => !!candidate);
  const value = selected?.[0] || null;
  const status = selected?.[1] || "Date unresolved";
  const date = value ? localDate(value, timezone) : null;
  const detail = value && "instant" in value
    ? new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: timezone }).format(new Date(value.instant)) + ` ${timezone}`
    : value ? "All day" : milestone.schedule.kind === "event_relative"
      ? `Relative to ${milestone.schedule.anchor_milestone_id}` : "Waiting for a date";
  return {
    id: milestone.id,
    title: milestone.kind.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()),
    date,
    detail,
    status,
    category: "milestone",
    source: milestone.evidence_ids.length ? `${milestone.evidence_ids.length} linked source(s)` : "Deal milestone",
  };
}

function paymentEvent(term: S["PaymentTerm"], timezone: string): CalendarEvent {
  const value = term.schedule.kind === "fixed" ? term.schedule.due : null;
  const when = value && "instant" in value
    ? new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: timezone }).format(new Date(value.instant)) + ` ${timezone}`
    : value ? "All day" : "Date depends on another milestone";
  return {
    id: term.id,
    title: term.side === "buyer" ? "Buyer payment" : term.side === "supplier" ? "Supplier payment" : "Production payment",
    date: value ? localDate(value, timezone) : null,
    detail: `${term.amount ? `${term.amount.currency} ${term.amount.amount} · ` : "Amount pending · "}${when}`,
    status: term.status === "agreed" ? "Agreed schedule" : "Proposed schedule",
    dateStatus: term.status === "agreed" ? "Agreed date" : "Proposed date",
    category: "payment",
    amount: term.amount ? `${term.amount.currency} ${term.amount.amount}` : undefined,
    direction: term.side === "buyer" ? "in" : "out",
    source: "Deal payment terms",
  };
}

function cashEvent(
  point: S["CashTimelinePoint"],
  index: number,
  timezone: string,
  deal: S["Deal"] | null,
  obligations: S["Obligation"][],
  receipts: S["Receipt"][],
  funding: S["FundingOption"][],
): CalendarEvent {
  const sourceId = point.source_ref?.id;
  const obligation = obligations.find((row) => row.id === sourceId);
  const receipt = receipts.find((row) => row.id === sourceId);
  const option = funding.find((row) => row.id === sourceId);
  const term = deal?.payment_terms.find((row) => row.id === sourceId);
  const partyId = obligation
    ? point.direction === "in" ? obligation.payer_party_id : obligation.payee_party_id
    : term ? point.direction === "in" ? term.payer_id : term.payee_id : null;
  const counterparty = deal?.parties.find((party) => party.id === partyId)?.display_name;
  const financing = !!option;
  const title = financing
    ? point.direction === "in" ? "Simulated loan draw" : "Simulated repayment"
    : term?.side === "buyer" ? "Buyer payment"
    : term?.side === "supplier" ? "Supplier payment"
    : term?.side === "production_input" ? "Production payment"
    : receipt ? "Verified receipt" : point.direction === "in" ? "Cash in" : "Cash out";
  const amount = `${point.amount.currency} ${point.amount.amount}`;
  return {
    id: `${sourceId || "cash"}-${index}`,
    title,
    date: localDate({ instant: point.at, timezone }, timezone),
    detail: new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: timezone }).format(new Date(point.at)) + ` ${timezone}`,
    status: financing ? "Simulated" : receipt ? receipt.status : obligation ? obligation.status : "Expected",
    dateStatus: financing ? "Simulated date" : receipt ? "Verified settlement instant" : "Projected date",
    category: financing ? "financing" : "payment",
    amount,
    balance: `${point.balance.currency} ${point.balance.amount}`,
    direction: point.direction,
    source: financing ? "Funding scenario" : receipt ? "Receipt evidence" : obligation ? "Payment obligation" : "Analysis cash event",
    counterparty,
  };
}

export function MilestoneCalendar({
  milestones,
  paymentTerms = [],
  cashPoints,
  unresolvedObligationIds = [],
  deal = null,
  obligations = [],
  receipts = [],
  funding = [],
  timezone,
  onCashTimeline,
}: {
  milestones: S["Milestone"][];
  paymentTerms?: S["PaymentTerm"][];
  cashPoints?: S["CashTimelinePoint"][];
  unresolvedObligationIds?: string[];
  deal?: S["Deal"] | null;
  obligations?: S["Obligation"][];
  receipts?: S["Receipt"][];
  funding?: S["FundingOption"][];
  timezone: string;
  onCashTimeline?: () => void;
}) {
  const events: CalendarEvent[] = [
    ...milestones.map((milestone) => eventFor(milestone, timezone)),
    ...(cashPoints
      ? cashPoints.map((point, index) => cashEvent(point, index, timezone, deal, obligations, receipts, funding))
      : paymentTerms.filter((term) => term.status !== "superseded").map((term) => paymentEvent(term, timezone))),
    ...unresolvedObligationIds.map((id): CalendarEvent => {
      const obligation = obligations.find((row) => row.id === id);
      const term = paymentTerms.find((row) => row.id === id);
      const direction = term?.side === "buyer" ? "in" : "out";
      return {
        id: `unresolved-${id}`,
        title: term?.side === "buyer" ? "Buyer payment" : "Payment obligation",
        date: null,
        detail: "Payment date unresolved",
        status: obligation?.status || "Expected",
        dateStatus: "Unscheduled",
        category: "payment",
        amount: obligation?.amount ? `${obligation.amount.currency} ${obligation.amount.amount}` : undefined,
        direction,
        source: "Payment obligation",
      };
    }),
  ];
  const [filter, setFilter] = useState<"all" | "payment" | "milestone">("all");
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);
  const filteredEvents = events.filter((event) => filter === "all" || (filter === "milestone" ? event.category === "milestone" : event.category !== "milestone"));
  const selectedEvent = events.find((event) => `${event.category}-${event.id}` === selectedEventId);
  const today = localDate({ instant: new Date().toISOString(), timezone }, timezone);
  const datedEvents = events.filter((event) => event.date)
    .sort((a, b) => a.date!.localeCompare(b.date!));
  const initialMonth = datedEvents.find((event) => event.date! >= today)?.date?.slice(0, 7)
    || datedEvents.at(-1)?.date?.slice(0, 7)
    || today.slice(0, 7);
  const [month, setMonth] = useState(initialMonth);
  const [year, monthNumber] = month.split("-").map(Number);
  const firstDay = new Date(Date.UTC(year, monthNumber - 1, 1)).getUTCDay();
  const offset = (firstDay + 6) % 7;
  const daysInMonth = new Date(Date.UTC(year, monthNumber, 0)).getUTCDate();
  const cells = Array.from({ length: Math.ceil((offset + daysInMonth) / 7) * 7 }, (_, index) => {
    const day = index - offset + 1;
    return day >= 1 && day <= daysInMonth ? day : null;
  });
  const monthEvents = filteredEvents.filter((event) => event.date?.startsWith(month))
    .sort((a, b) => a.date!.localeCompare(b.date!) || a.title.localeCompare(b.title));
  const undated = filteredEvents.filter((event) => !event.date);
  const monthLabel = new Intl.DateTimeFormat("en-GB", { month: "long", year: "numeric", timeZone: "UTC" })
    .format(new Date(Date.UTC(year, monthNumber - 1, 1)));
  function moveMonth(delta: number) {
    const next = new Date(Date.UTC(year, monthNumber - 1 + delta, 1));
    setMonth(`${next.getUTCFullYear()}-${String(next.getUTCMonth() + 1).padStart(2, "0")}`);
  }
  return (
    <section className="card milestone-calendar" aria-label="Milestone calendar">
      <div className="calendar-heading">
        <div>
          <h2>{monthLabel}</h2>
          <p className="muted">{milestones.length} milestone{milestones.length === 1 ? "" : "s"} · {events.length - milestones.length} cash event{events.length - milestones.length === 1 ? "" : "s"} · {timezone}</p>
        </div>
        <div className="actions">
          <button className="secondary" aria-label="Previous month" onClick={() => moveMonth(-1)}>←</button>
          <button className="secondary" onClick={() => setMonth(today.slice(0, 7))}>Today</button>
          <button className="secondary" aria-label="Next month" onClick={() => moveMonth(1)}>→</button>
        </div>
      </div>
      <div className="calendar-filters" role="group" aria-label="Calendar event filter">
        {([ ["all", "All events"], ["payment", "Payments & financing"], ["milestone", "Milestones"] ] as const).map(([value, label]) => (
          <button className="secondary" key={value} aria-pressed={filter === value} onClick={() => setFilter(value)}>{label}</button>
        ))}
      </div>
      <div className="calendar-grid" aria-label={monthLabel}>
        {(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"] as const).map((day) => <div className="calendar-weekday" key={day}>{day}</div>)}
        {cells.map((day, index) => {
          const date = day ? `${month}-${String(day).padStart(2, "0")}` : null;
          const onDay = filteredEvents.filter((event) => event.date === date);
          return (
            <div key={index} className={`calendar-day${day ? "" : " outside"}${date === today ? " today" : ""}`}>
              {day && <span className="calendar-day-number">{day}</span>}
              {onDay.map((event) => <button type="button" className={`calendar-event ${event.category}`} key={`${event.category}-${event.id}`} aria-label={`${event.title}, ${date}, ${event.amount || "milestone"}`} title={`${event.title} · ${event.status} · ${event.detail}`} onClick={() => setSelectedEventId(`${event.category}-${event.id}`)}>{event.title}</button>)}
            </div>
          );
        })}
      </div>
      <div className="calendar-agenda">
        <h3>Happening this month</h3>
        {monthEvents.length ? monthEvents.map((event) => (
          <article key={`${event.category}-${event.id}`}>
            <time dateTime={event.date!}>{new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short", timeZone: "UTC" }).format(new Date(`${event.date}T12:00:00Z`))}</time>
            <div>
              <button className="link" onClick={() => setSelectedEventId(`${event.category}-${event.id}`)}>{event.title}{event.amount ? ` · ${event.amount}` : ""}</button>
              <small>{event.status} · {event.detail}</small>
            </div>
          </article>
        )) : <p className="muted">No scheduled events in this month. Use the arrows to browse other months.</p>}
        {!!undated.length && (
          <>
            <h3>Waiting for dates</h3>
            {undated.map((event) => <article key={`${event.category}-${event.id}`}><span>—</span><div><strong>{event.title}</strong><small>{event.detail}</small></div></article>)}
          </>
        )}
        {!milestones.length && <p className="muted">No milestones recorded yet. Add a milestone in Readiness & timeline to put it on this calendar.</p>}
      </div>
      {selectedEvent && (
        <aside className="calendar-event-detail" aria-label="Selected calendar event">
          <div className="row">
            <div><span className="eyebrow">{selectedEvent.category === "milestone" ? "MILESTONE" : selectedEvent.category === "financing" ? "SIMULATED FINANCING" : "CASH EVENT"}</span><h3>{selectedEvent.title}</h3></div>
            <button className="secondary" onClick={() => setSelectedEventId(null)} aria-label="Close event details">Close</button>
          </div>
          <dl>
            <div><dt>Date</dt><dd>{selectedEvent.date || "Unscheduled"} · {selectedEvent.detail}</dd></div>
            {selectedEvent.amount && <div><dt>Amount</dt><dd>{selectedEvent.direction === "in" ? "+" : "−"}{selectedEvent.amount}</dd></div>}
            <div><dt>Date basis</dt><dd>{selectedEvent.dateStatus || selectedEvent.status}</dd></div>
            {selectedEvent.category !== "milestone" && <div><dt>Payment status</dt><dd>{selectedEvent.status}</dd></div>}
            <div><dt>Source</dt><dd>{selectedEvent.source}</dd></div>
            {selectedEvent.counterparty && <div><dt>Counterparty</dt><dd>{selectedEvent.counterparty}</dd></div>}
            {selectedEvent.balance && <div><dt>Balance after event</dt><dd>{selectedEvent.balance}</dd></div>}
          </dl>
          {onCashTimeline && selectedEvent.balance && <button onClick={onCashTimeline}>View cash timeline →</button>}
        </aside>
      )}
    </section>
  );
}
