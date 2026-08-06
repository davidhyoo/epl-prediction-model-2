import type { Outcome, RankingKey } from "./types";

/** Format a 0-1 probability as a whole-number percentage string. */
export function pct(value: number, digits = 0): string {
  return `${(value * 100).toFixed(digits)}%`;
}

/** Format a value that is already a percentage number (0-100). */
export function pctRaw(value: number, digits = 0): string {
  return `${value.toFixed(digits)}%`;
}

/** Format a 0-1 probability as a percentage number (no unit). */
export function pctNum(value: number, digits = 1): number {
  return Number((value * 100).toFixed(digits));
}

/**
 * Format a season-odds fraction (0-1, as written to clubs.json) as a percent.
 * Small non-zero odds keep one decimal so "3.2%" doesn't collapse to "3%".
 */
export function oddsPct(value: number): string {
  const p = value * 100;
  if (p > 0 && p < 10) return `${p.toFixed(1)}%`;
  return `${p.toFixed(0)}%`;
}

/** Bar width (0-100) for a season-odds fraction, with a visible minimum. */
export function oddsWidth(value: number, min = 1.5): number {
  return Math.max(min, value * 100);
}

export function formatNumber(value: number, digits = 0): string {
  return value.toLocaleString("en-US", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

/** Compact, locale-aware date/time for match cards (UTC → deterministic). */
export function formatMatchDate(iso: string): { date: string; time: string; weekday: string } {
  const d = new Date(iso);
  return {
    weekday: d.toLocaleDateString("en-US", { weekday: "short", timeZone: "UTC" }),
    date: d.toLocaleDateString("en-US", { month: "short", day: "numeric", timeZone: "UTC" }),
    time: d.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
      hour12: false,
      timeZone: "UTC",
    }),
  };
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  });
}

export function formatRelative(iso: string): string {
  const then = new Date(iso).getTime();
  const now = Date.now();
  const diff = now - then;
  const mins = Math.round(diff / 60000);
  if (Math.abs(mins) < 60) return `${Math.abs(mins)}m ago`;
  const hours = Math.round(mins / 60);
  if (Math.abs(hours) < 24) return `${Math.abs(hours)}h ago`;
  const days = Math.round(hours / 24);
  return `${Math.abs(days)}d ago`;
}

export const OUTCOME_LABEL: Record<Outcome, string> = {
  home: "Home win",
  draw: "Draw",
  away: "Away win",
};

/** Ensure a hex colour has enough contrast to sit on a card. */
export function readableColor(hex: string): string {
  const c = (hex || "").replace("#", "");
  if (c.length !== 6) return hex;
  const r = parseInt(c.slice(0, 2), 16);
  const g = parseInt(c.slice(2, 4), 16);
  const b = parseInt(c.slice(4, 6), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.82 ? "#64748b" : hex;
}

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

/** Deterministic hue from a string (for placeholder avatars). */
export function stringToHue(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return Math.abs(hash) % 360;
}

/** Position → sort order + colour bucket. */
export const POSITION_ORDER: Record<string, number> = { GK: 0, DEF: 1, MID: 2, FWD: 3 };

export const POSITION_LABEL: Record<string, string> = {
  GK: "Goalkeeper",
  DEF: "Defender",
  MID: "Midfielder",
  FWD: "Forward",
};

/** Human labels + descriptions for the ranking views. */
export const RANKING_META: Record<
  RankingKey,
  { label: string; description: string; unit: "percent" | "index" | "rating" }
> = {
  title: {
    label: "Title probability",
    description: "Monte-Carlo simulated chance of winning the league (10k seasons).",
    unit: "percent",
  },
  strength: {
    label: "Team strength",
    description: "Overall strength index blending Elo, form and goal record.",
    unit: "index",
  },
  form: {
    label: "Recent form",
    description: "Points won over the last five matches, indexed to the league.",
    unit: "index",
  },
  attack: {
    label: "Attack strength",
    description: "Goals-for rate relative to the rest of the division.",
    unit: "index",
  },
  defense: {
    label: "Defensive solidity",
    description: "Goals-against rate (inverted) relative to the division.",
    unit: "index",
  },
  squad: {
    label: "Squad quality",
    description: "Aggregated player-rating strength of the registered squad.",
    unit: "index",
  },
  elo: {
    label: "Elo rating",
    description: "World-Football-Elo rating after the latest completed match.",
    unit: "rating",
  },
  momentum: {
    label: "Momentum",
    description: "Trend in results — is the team climbing or sliding?",
    unit: "index",
  },
};

export const RANKING_ORDER: RankingKey[] = [
  "title",
  "strength",
  "form",
  "attack",
  "defense",
  "squad",
  "elo",
  "momentum",
];
