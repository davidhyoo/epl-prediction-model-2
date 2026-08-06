import { describe, it, expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { ProbabilityBar } from "@/components/probability-bar";

/**
 * Rendered to a static HTML string with react-dom/server so the suite stays in
 * a plain Node environment (no jsdom). We assert on the emitted markup, which
 * is sufficient to verify the labels and formatted percentages.
 */
describe("ProbabilityBar", () => {
  it("renders labels and formatted percentages for a match with a draw slice", () => {
    const html = renderToStaticMarkup(
      <ProbabilityBar
        homeProb={0.55}
        drawProb={0.25}
        awayProb={0.2}
        homeColor="#1e3a8a"
        awayColor="#b91c1c"
        homeLabel="ARS"
        awayLabel="CHE"
      />,
    );

    expect(html).toContain("ARS");
    expect(html).toContain("CHE");
    expect(html).toContain("55%");
    expect(html).toContain("Draw 25%");
  });

  it("hides the draw slice in two-way mode", () => {
    const html = renderToStaticMarkup(
      <ProbabilityBar
        homeProb={0.66}
        awayProb={0.34}
        homeColor="#1e3a8a"
        awayColor="#b91c1c"
        homeLabel="MCI"
        awayLabel="BUR"
        twoWay
      />,
    );

    expect(html).toContain("66%");
    expect(html).not.toContain("Draw");
  });
});
