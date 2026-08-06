import { describe, it, expect } from "vitest";
import {
  pct,
  pctNum,
  oddsPct,
  oddsWidth,
  formatNumber,
  formatMatchDate,
  formatDateTime,
  readableColor,
  initials,
  stringToHue,
  POSITION_LABEL,
  RANKING_META,
  RANKING_ORDER,
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

describe("oddsPct (0-1 season odds → percent)", () => {
  it("formats mid/large odds with no decimals", () => {
    expect(oddsPct(0.4329)).toBe("43%");
    expect(oddsPct(1)).toBe("100%");
    expect(oddsPct(0.1)).toBe("10%");
  });

  it("keeps one decimal for small non-zero odds so they don't vanish", () => {
    expect(oddsPct(0.032)).toBe("3.2%");
    expect(oddsPct(0.001)).toBe("0.1%");
    expect(oddsPct(0)).toBe("0%");
  });
});

describe("oddsWidth", () => {
  it("scales a fraction to a 0-100 bar width", () => {
    expect(oddsWidth(0.5)).toBe(50);
    expect(oddsWidth(1)).toBe(100);
  });

  it("enforces a visible minimum for tiny odds", () => {
    expect(oddsWidth(0)).toBe(1.5);
    expect(oddsWidth(0.001, 2)).toBe(2);
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
    const parts = formatMatchDate("2026-08-15T18:00:00Z");
    expect(parts.date).toBe("Aug 15");
    expect(parts.time).toBe("18:00");
    expect(parts.weekday).toBe("Sat");
  });

  it("renders a long UTC date", () => {
    expect(formatDateTime("2026-08-15T00:00:00Z")).toBe("August 15, 2026");
  });
});

describe("readableColor", () => {
  it("passes through colours with enough contrast", () => {
    expect(readableColor("#1e3a8a")).toBe("#1e3a8a");
  });

  it("darkens near-white colours so they stay legible", () => {
    expect(readableColor("#ffffff")).toBe("#64748b");
  });

  it("returns the input unchanged when it is not a 6-digit hex", () => {
    expect(readableColor("rebeccapurple")).toBe("rebeccapurple");
  });
});

describe("initials", () => {
  it("uses first and last name initials", () => {
    expect(initials("Erling Haaland")).toBe("EH");
    expect(initials("Bukayo Saka")).toBe("BS");
  });

  it("falls back to the first two letters for single names", () => {
    expect(initials("Rodri")).toBe("RO");
  });
});

describe("stringToHue", () => {
  it("is deterministic and within [0, 360)", () => {
    const a = stringToHue("Arsenal");
    const b = stringToHue("Arsenal");
    expect(a).toBe(b);
    expect(a).toBeGreaterThanOrEqual(0);
    expect(a).toBeLessThan(360);
  });
});

describe("domain constants", () => {
  it("labels the four positions", () => {
    expect(POSITION_LABEL.GK).toBe("Goalkeeper");
    expect(POSITION_LABEL.FWD).toBe("Forward");
  });

  it("exposes eight ranking views in order, each with metadata", () => {
    expect(RANKING_ORDER[0]).toBe("title");
    expect(RANKING_ORDER).toHaveLength(8);
    for (const key of RANKING_ORDER) {
      expect(RANKING_META[key].label).toBeTruthy();
      expect(["percent", "index", "rating"]).toContain(RANKING_META[key].unit);
    }
  });

  it("labels all three outcomes", () => {
    expect(OUTCOME_LABEL.home).toBe("Home win");
    expect(OUTCOME_LABEL.draw).toBe("Draw");
    expect(OUTCOME_LABEL.away).toBe("Away win");
  });
});
