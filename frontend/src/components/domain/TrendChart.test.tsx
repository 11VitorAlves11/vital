import { screen } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";

import type { Intervention } from "../../lib/api/types";
import { renderWithProviders, usePortuguese } from "../../test/utils";
import { interventionOverlayElements, referenceBandElements } from "./ReferenceBand";
import { TrendChart } from "./TrendChart";

const CREATINE: Intervention = {
  id: "abc",
  kind: "suplemento",
  name: "Creatina",
  dose: "5 g/dia",
  started_on: "2026-01-01",
  ended_on: "2026-03-01",
  notes: null,
};

const POINTS = [
  { timestamp: Date.parse("2026-01-15"), value: 14, refMin: 13, refMax: 17 },
  { timestamp: Date.parse("2026-06-15"), value: 15.5, refMin: 13, refMax: 17 },
];

beforeAll(async () => {
  await usePortuguese();
});

describe("TrendChart", () => {
  it("summarises the trend for anyone who cannot see it", () => {
    renderWithProviders(
      <TrendChart name="Hemoglobina" unit="g/dL" points={POINTS} interventions={[]} />,
    );
    const chart = screen.getByRole("img");
    expect(chart.getAttribute("aria-label")).toContain("Hemoglobina");
    expect(chart.getAttribute("aria-label")).toContain("14");
    expect(chart.getAttribute("aria-label")).toContain("15,5");
  });

  it("is reachable by keyboard", () => {
    renderWithProviders(
      <TrendChart name="Hemoglobina" unit="g/dL" points={POINTS} interventions={[]} />,
    );
    expect(screen.getByRole("img")).toHaveAttribute("tabindex", "0");
  });
});

describe("referenceBandElements", () => {
  it("draws the limits as labelled lines, not only as shading", () => {
    const elements = referenceBandElements({
      hasLabRange: true,
      canonicalMin: 13,
      canonicalMax: 17,
      minLabel: (value) => `Mín. ${value}`,
      maxLabel: (value) => `Máx. ${value}`,
    });
    const keys = elements.map((element) => element.key);
    expect(keys).toEqual(["lab-range", "canonical-min", "canonical-max"]);

    const [, min, max] = elements;
    expect(min.props.strokeDasharray).toBe("6 4");
    expect(min.props.label.value).toBe("Mín. 13");
    expect(max.props.label.value).toBe("Máx. 17");
  });

  it("omits the shaded area when no lab reported a range", () => {
    const elements = referenceBandElements({
      hasLabRange: false,
      canonicalMin: null,
      canonicalMax: null,
      minLabel: String,
      maxLabel: String,
    });
    expect(elements).toHaveLength(0);
  });
});

describe("interventionOverlayElements", () => {
  it("labels each band with its name and dose", () => {
    const [band] = interventionOverlayElements({
      interventions: [CREATINE],
      domainStart: Date.parse("2026-01-10"),
      domainEnd: Date.parse("2026-06-15"),
    });
    expect(band.props.label.value).toBe("Creatina · 5 g/dia");
  });

  it("clamps the band to the plotted period", () => {
    const domainStart = Date.parse("2026-02-01");
    const domainEnd = Date.parse("2026-02-20");
    const [band] = interventionOverlayElements({
      interventions: [CREATINE],
      domainStart,
      domainEnd,
    });
    // Started before and ended after the window: it may not imply data that is
    // not on the chart.
    expect(band.props.x1).toBe(domainStart);
    expect(band.props.x2).toBe(domainEnd);
  });

  it("runs an open intervention to the end of the period", () => {
    const domainEnd = Date.parse("2026-06-15");
    const [band] = interventionOverlayElements({
      interventions: [{ ...CREATINE, ended_on: null }],
      domainStart: Date.parse("2026-01-01"),
      domainEnd,
    });
    expect(band.props.x2).toBe(domainEnd);
  });
});
