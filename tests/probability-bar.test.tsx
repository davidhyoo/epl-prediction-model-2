import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProbabilityBar } from "@/components/probability-bar";

describe("ProbabilityBar", () => {
  it("renders labels and formatted percentages for a group-stage match", () => {
    render(
      <ProbabilityBar
        homeProb={0.55}
        drawProb={0.25}
        awayProb={0.2}
        homeColor="#1e3a8a"
        awayColor="#b91c1c"
        homeLabel="BRA"
        awayLabel="SRB"
      />,
    );

    expect(screen.getByText("BRA")).toBeInTheDocument();
    expect(screen.getByText("SRB")).toBeInTheDocument();
    expect(screen.getByText("55%")).toBeInTheDocument();
    expect(screen.getByText("Draw 25%")).toBeInTheDocument();
  });

  it("hides the draw slice in two-way (knockout) mode", () => {
    render(
      <ProbabilityBar
        homeProb={0.66}
        awayProb={0.34}
        homeColor="#1e3a8a"
        awayColor="#b91c1c"
        homeLabel="BEL"
        awayLabel="PAN"
        twoWay
      />,
    );

    expect(screen.getByText("66%")).toBeInTheDocument();
    expect(screen.queryByText(/Draw/)).not.toBeInTheDocument();
  });
});
