"use client";

import type { components } from "../../../../packages/contracts/api";

type Point = components["schemas"]["CashTimelinePoint"];

export function CashBalanceChart({ points, currency }: { points: Point[]; currency: string }) {
  if (!points.length) return null;
  const width = 740;
  const height = 230;
  const left = 44;
  const right = 20;
  const top = 18;
  const bottom = 32;
  const first = new Date(points[0].at).getTime();
  const last = new Date(points.at(-1)!.at).getTime();
  const startingBalance = Number(points[0].balance.amount)
    + (points[0].direction === "out" ? 1 : -1) * Number(points[0].amount.amount);
  const balances = [startingBalance, ...points.map((point) => Number(point.balance.amount))];
  const low = Math.min(0, ...balances);
  const high = Math.max(0, ...balances);
  const padding = Math.max(1, (high - low) * 0.12);
  const lower = low - padding;
  const upper = high + padding;
  const x = (instant: string) => last === first
    ? left + (width - left - right) / 2
    : left + ((new Date(instant).getTime() - first) / (last - first)) * (width - left - right);
  const y = (balance: number) => top + ((upper - balance) / (upper - lower)) * (height - top - bottom);
  const path = points.reduce((shape, point) => `${shape} H ${x(point.at).toFixed(2)} V ${y(Number(point.balance.amount)).toFixed(2)}`, `M ${left} ${y(startingBalance).toFixed(2)}`);
  const dateLabel = (instant: string) => new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "short" }).format(new Date(instant));
  return (
    <div className="cash-chart-wrap">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`Projected cash balance in ${currency}. Lowest balance ${currency} ${Math.min(...balances)}.`}>
        <line x1={left} x2={width - right} y1={y(0)} y2={y(0)} className="cash-chart-zero" />
        <text x={left - 8} y={y(0) + 4} textAnchor="end">0</text>
        <path d={path} className="cash-chart-line" />
        {points.map((point, index) => (
          <circle key={`${point.at}-${index}`} cx={x(point.at)} cy={y(Number(point.balance.amount))} r="4" className={Number(point.balance.amount) < 0 ? "cash-chart-point negative" : "cash-chart-point"}>
            <title>{dateLabel(point.at)} · {currency} {point.balance.amount}</title>
          </circle>
        ))}
        <text x={left} y={height - 8}>{dateLabel(points[0].at)}</text>
        <text x={width - right} y={height - 8} textAnchor="end">{dateLabel(points.at(-1)!.at)}</text>
      </svg>
      <p className="muted">Projected balance after each cash event. Dates follow the selected analysis.</p>
    </div>
  );
}
