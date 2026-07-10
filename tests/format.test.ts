import { describe, it, expect } from "vitest";
import {
  pct,
  pctNum,
  formatNumber,
  formatMatchDate,
  formatDateTime,
  readableColor,
  initials,
  stringToHue,
  STAGE_ORDER,
  STAGE_SHORT,
  OUTCOME_LABEL,
} from "@/lib/format";

describe("pct", () => {
  it("formats a 0-1 probability as a whole percentage", () => {
    expect(pct(0.5)).toBe("50%");
    expect(pct(0.279)).toBe("28%");
    expect(pct(0)).toBe("0%");
    expect(pct(1)).toBe("100%");
  });

  it("honours the digits argument", () => {
    expect(pct(0.2799, 1)).toBe("28.0%");
    expect(pct(0.12345, 2)).toBe("12.35%");
  });
});

describe("pctNum", () => {
  it("returns a numeric percentage rounded to one decimal", () => {
    expect(pctNum(0.5)).toBe(50);
    expect(pctNum(0.27975)).toBe(28);
    expect(pctNum(0.12345, 2)).toBe(12.35);
  });
});

describe("formatNumber", () => {
  it("adds thousands separators", () => {
    expect(formatNumber(1248)).toBe("1,248");
    expect(formatNumber(20000)).toBe("20,000");
  });
});

describe("formatMatchDate / formatDateTime", () => {
  it("renders UTC-stable date parts", () => {
    const parts = formatMatchDate("2026-06-27T18:00:00Z");
    expect(parts.date).toBe("Jun 27");
    expect(parts.time).toBe("18:00");
    expect(parts.weekday).toBe("Sat");
  });

  it("renders a long UTC date", () => {
    expect(formatDateTime("2026-07-19T00:00:00Z")).toBe("July 19, 2026");
  });
});

describe("readableColor", () => {
  it("passes through colours with enough contrast", () => {
    expect(readableColor("#1e3a8a")).toBe("#1e3a8a");
  });

  it("darkens near-white colours so they stay legible", () => {
    expect(readableColor("#ffffff")).toBe("#334155");
  });

  it("returns the input unchanged when it is not a 6-digit hex", () => {
    expect(readableColor("rebeccapurple")).toBe("rebeccapurple");
  });
});

describe("initials", () => {
  it("uses first and last name initials", () => {
    expect(initials("Kylian Mbappe")).toBe("KM");
    expect(initials("Vinicius Junior")).toBe("VJ");
  });

  it("falls back to the first two letters for single names", () => {
    expect(initials("Ronaldinho")).toBe("RO");
  });
});

describe("stringToHue", () => {
  it("is deterministic and within [0, 360)", () => {
    const a = stringToHue("Argentina");
    const b = stringToHue("Argentina");
    expect(a).toBe(b);
    expect(a).toBeGreaterThanOrEqual(0);
    expect(a).toBeLessThan(360);
  });
});

describe("stage + outcome constants", () => {
  it("orders stages from group to final", () => {
    expect(STAGE_ORDER[0]).toBe("group");
    expect(STAGE_ORDER[STAGE_ORDER.length - 1]).toBe("final");
    expect(STAGE_SHORT["round-of-32"]).toBe("R32");
  });

  it("labels all three outcomes", () => {
    expect(OUTCOME_LABEL.home).toBe("Home win");
    expect(OUTCOME_LABEL.draw).toBe("Draw");
    expect(OUTCOME_LABEL.away).toBe("Away win");
  });
});
