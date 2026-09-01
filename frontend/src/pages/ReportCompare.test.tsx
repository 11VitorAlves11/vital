import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it } from "vitest";

import { mockApi, renderWithProviders, setViewport, usePortuguese } from "../test/utils";
import { ReportCompare } from "./ReportCompare";

function summary(id: string, collected_on: string) {
  return {
    id,
    collected_on,
    collected_at: null,
    lab_id: "l1",
    lab_name: "Synlab Braga",
    doctor_id: null,
    doctor_name: null,
    fasting_state: "fasting",
    fasting_hours: null,
    source: "manual",
    notes: null,
    notes_at: null,
    created_at: `${collected_on}T10:00:00Z`,
    result_count: 1,
    has_file: false,
  };
}

function result(overrides: object = {}) {
  return {
    id: "res-1",
    biomarker_id: 1,
    biomarker_slug: "ferritina",
    biomarker_name: "Ferritina",
    category: "ferro",
    value: "40.0000",
    unit: "ng/mL",
    canonical_value: "40.0000",
    canonical_unit: "ng/mL",
    ref_min: "15.0000",
    ref_max: "150.0000",
    reference_kind: "two_sided",
    reference_bands: null,
    band_label: null,
    method: null,
    note: null,
    note_at: null,
    caveats: [],
    flag: "normal",
    ...overrides,
  };
}

function row(overrides: object = {}) {
  return {
    biomarker_id: 1,
    biomarker_slug: "ferritina",
    biomarker_name: "Ferritina",
    category: "ferro",
    previous: result(),
    current: result({ id: "res-2", value: "30.0000", canonical_value: "30.0000" }),
    delta: "-10.0000",
    percent_change: "-25.00",
    unit: "ng/mL",
    caveats: [],
    ...overrides,
  };
}

const REPORTS = [summary("r2", "2026-06-10"), summary("r1", "2026-01-10")];

function comparison(rows: object[]) {
  return { previous: summary("r1", "2026-01-10"), current: summary("r2", "2026-06-10"), rows };
}

beforeAll(async () => {
  await usePortuguese();
});

/** Order matters: the comparison pattern is the narrower of the two. */
function render(
  rows: object[] = [row()],
  { route = "/reports/compare", list = REPORTS }: { route?: string; list?: object[] } = {},
) {
  const fetchMock = mockApi([
    { pattern: /\/api\/reports\/compare/, body: comparison(rows) },
    { pattern: /\/api\/reports/, body: list },
  ]);
  renderWithProviders(<ReportCompare />, { route });
  return fetchMock;
}

function compareCall(fetchMock: ReturnType<typeof mockApi>) {
  return fetchMock.mock.calls.map(([url]) => String(url)).find((url) => url.includes("compare"));
}

describe("ReportCompare", () => {
  it("compares the two most recent collections without being asked", async () => {
    const fetchMock = render();
    await waitFor(() => expect(compareCall(fetchMock)).toBeDefined());
    const url = new URL(compareCall(fetchMock) ?? "", "http://test");
    expect([url.searchParams.get("a"), url.searchParams.get("b")]).toEqual(["r1", "r2"]);
  });

  it("takes the neighbouring draw when only one collection is named", async () => {
    // The link from a report's own page carries just that report.
    const fetchMock = render([row()], { route: "/reports/compare?b=r2" });
    await waitFor(() => expect(compareCall(fetchMock)).toBeDefined());
    const url = new URL(compareCall(fetchMock) ?? "", "http://test");
    expect(url.searchParams.get("a")).toBe("r2");
    expect(url.searchParams.get("b")).toBe("r1");
  });

  it("shows both values, the difference and the change", async () => {
    setViewport("desktop");
    render();
    const line = await screen.findByRole("row", { name: /Ferritina/ });
    expect(within(line).getByText("40")).toBeInTheDocument();
    expect(within(line).getByText("30")).toBeInTheDocument();
    expect(line).toHaveTextContent("-10");
    expect(line).toHaveTextContent("-25%");
  });

  it("stacks the rows on a phone, where five columns do not fit", async () => {
    render();
    // The difference is the point of the page; in a table it would sit off the
    // right edge of the screen.
    expect(await screen.findByText(/-10/)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.getAllByText("10/01/2026").length).toBeGreaterThan(0);
  });

  it("shows the converted value when the two draws used different units", async () => {
    render([
      row({
        previous: result({ value: "140.0000", unit: "g/L", canonical_value: "14.0000" }),
        current: result({ id: "res-2", value: "15.1000", canonical_value: "15.1000" }),
        delta: "1.1000",
        percent_change: "7.86",
        unit: "ng/mL",
      }),
    ]);
    // 140 g/L is not a fall to 15,1: the scale the difference was taken on is
    // spelled out beside the value as reported.
    expect(await screen.findByText("= 14 ng/mL")).toBeInTheDocument();
  });

  it("marks a marker that only one of the collections measured", async () => {
    render([
      row({ current: null, delta: null, percent_change: null, unit: null }),
      row({
        biomarker_id: 2,
        biomarker_slug: "hemoglobina",
        biomarker_name: "Hemoglobina",
        category: "hematologia",
        previous: null,
        delta: null,
        percent_change: null,
        unit: null,
      }),
    ]);
    expect(await screen.findByText("Não repetido")).toBeInTheDocument();
    expect(screen.getByText("Novo")).toBeInTheDocument();
  });

  it("says why a difference may not be a difference", async () => {
    render([
      row({
        current: result({ id: "res-2", value: "40.0000", flag: "high", ref_max: "35.0000" }),
        delta: "0.0000",
        percent_change: "0.00",
        caveats: [{ code: "reference_changed", values: {} }],
      }),
    ]);
    // The caveat, and the two intervals it is about — shown only on the rows
    // where they moved.
    expect(await screen.findByText(/intervalo de referência não é o mesmo/)).toBeInTheDocument();
    expect(screen.getByText("15–150")).toBeInTheDocument();
    expect(screen.getByText("15–35")).toBeInTheDocument();
  });

  it("counts what crossed the interval, in each direction", async () => {
    render([
      row({ previous: result({ flag: "high" }), current: result({ id: "res-2", flag: "normal" }) }),
      row({
        biomarker_id: 2,
        biomarker_name: "Hemoglobina",
        biomarker_slug: "hemoglobina",
        category: "hematologia",
        previous: result({ flag: "normal" }),
        current: result({ id: "res-3", flag: "low" }),
      }),
    ]);
    expect(await screen.findByText(/1 saiu do intervalo/)).toBeInTheDocument();
    expect(screen.getByText(/1 entrou no intervalo/)).toBeInTheDocument();
  });

  it("asks for another collection when there is only one", async () => {
    render([], { list: [summary("r1", "2026-01-10")] });
    expect(await screen.findByText("Ainda não há duas colheitas para comparar")).toBeInTheDocument();
  });

  it("does not compare a collection with itself", async () => {
    const fetchMock = render();
    await screen.findByText("Ferritina");
    await userEvent.selectOptions(screen.getByLabelText("Primeira colheita"), "r2");

    expect(await screen.findByText(/Escolhe duas colheitas diferentes/)).toBeInTheDocument();
    expect(screen.queryByText("Ferritina")).not.toBeInTheDocument();
    const asked = fetchMock.mock.calls.map(([url]) => String(url));
    expect(asked.some((url) => url.includes("a=r2") && url.includes("b=r2"))).toBe(false);
  });
});
