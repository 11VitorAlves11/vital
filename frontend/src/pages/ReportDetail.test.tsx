import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it } from "vitest";

import { mockApi, renderWithProviders, usePortuguese } from "../test/utils";
import { ReportDetail } from "./ReportDetail";

const RESULT = {
  id: "res-1",
  biomarker_id: 1,
  biomarker_slug: "hemoglobina",
  biomarker_name: "Hemoglobina",
  category: "hematologia",
  value: "14.1000",
  unit: "g/dL",
  canonical_value: "14.1000",
  canonical_unit: "g/dL",
  ref_min: "13.0000",
  ref_max: "17.0000",
  reference_kind: "two_sided",
  reference_bands: null,
  band_label: null,
  method: null,
  note: null,
  note_at: null,
  caveats: [],
  flag: "normal",
};

const REPORT = {
  id: "r1",
  collected_on: "2026-03-01",
  collected_at: "2026-03-01T08:15:00",
  lab_id: "l1",
  lab_name: "Synlab Braga",
  doctor_id: "d1",
  doctor_name: "Dra. Sofia Nunes",
  fasting_state: "fasting",
  fasting_hours: 12,
  source: "manual",
  notes: null,
  notes_at: null,
  created_at: "2026-03-01T10:00:00Z",
  has_file: false,
  results: [RESULT],
};

beforeAll(async () => {
  await usePortuguese();
});

function render(report: object = REPORT) {
  const fetchMock = mockApi([{ pattern: /\/api\/reports\/r1/, body: report }]);
  renderWithProviders(<ReportDetail />, { route: "/reports/r1", path: "/reports/:id" });
  return fetchMock;
}

describe("ReportDetail", () => {
  it("states the collection context in one line", async () => {
    render();
    await screen.findByRole("heading", { level: 1 });
    // Where, at what hour, in what state — the laboratory and the doctor as
    // entities, not as free text repeated on every report.
    const line = screen.getByText(/Synlab Braga/);
    expect(line).toHaveTextContent("Dra. Sofia Nunes");
    expect(line).toHaveTextContent("08:15");
    expect(line).toHaveTextContent("Em jejum");
    expect(line).toHaveTextContent("12 h de jejum");
  });

  it("leaves out what nobody recorded", async () => {
    render({
      ...REPORT,
      collected_at: null,
      doctor_name: null,
      fasting_state: "unknown",
      fasting_hours: null,
    });
    const line = await screen.findByText(/Synlab Braga/);
    expect(line).toHaveTextContent("Synlab Braga");
    expect(line).not.toHaveTextContent("·");
  });

  it("writes the note on the collection as a whole", async () => {
    const fetchMock = render();
    await userEvent.click((await screen.findAllByRole("button", { name: "Adicionar nota" }))[0]);
    await userEvent.type(screen.getByRole("textbox"), "Ferritina a subir.");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, init]) => init?.method === "PATCH");
      expect(call?.[0]).toBe("/api/reports/r1");
      expect(JSON.parse(String(call?.[1]?.body))).toEqual({ notes: "Ferritina a subir." });
    });
  });

  it("writes a note against one value, at its own endpoint", async () => {
    const fetchMock = render();
    const buttons = await screen.findAllByRole("button", { name: "Adicionar nota" });
    // The second is the one beside the result; the first belongs to the report.
    await userEvent.click(buttons[1]);
    await userEvent.type(screen.getByRole("textbox"), "Colheita às 11:30.");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, init]) => init?.method === "PATCH");
      expect(call?.[0]).toBe("/api/reports/r1/results/res-1");
      expect(JSON.parse(String(call?.[1]?.body))).toEqual({ note: "Colheita às 11:30." });
    });
  });

  it("says when an existing note was written", async () => {
    render({ ...REPORT, notes: "Tudo dentro do intervalo.", notes_at: "2026-03-02T09:30:00Z" });
    expect(await screen.findByText("Tudo dentro do intervalo.")).toBeInTheDocument();
    expect(screen.getByText(/Escrita em/)).toBeInTheDocument();
  });

  it("shows a computed value with no note editor and no repeat action", async () => {
    const derived = {
      ...RESULT,
      id: null,
      biomarker_id: 5,
      biomarker_slug: "ldl",
      biomarker_name: "Colesterol LDL",
      value: "140.0000",
      canonical_value: "140.0000",
      ref_min: null,
      ref_max: "115.0000",
      flag: "high",
      derived_from: ["Colesterol total", "Colesterol HDL", "Triglicéridos"],
    };
    render({ ...REPORT, results: [RESULT, derived] });

    await screen.findByText("Colesterol LDL");
    expect(
      screen.getByText("Calculado a partir de Colesterol total, Colesterol HDL e Triglicéridos"),
    ).toBeInTheDocument();
    // One "Adicionar nota" for the report itself, one for the real result —
    // the derived row adds neither that nor a repeat action of its own.
    const buttons = screen.getAllByRole("button", { name: "Adicionar nota" });
    expect(buttons).toHaveLength(2);
    const scheduleButtons = screen.getAllByRole("button", { name: "Agendar repetição" });
    expect(scheduleButtons).toHaveLength(1);
  });

  it("schedules a repeat from one result", async () => {
    const fetchMock = mockApi([
      { pattern: /\/api\/repeats/, body: { id: "rep-1" } },
      { pattern: /\/api\/reports\/r1/, body: REPORT },
    ]);
    renderWithProviders(<ReportDetail />, { route: "/reports/r1", path: "/reports/:id" });

    await userEvent.click(await screen.findByRole("button", { name: "Agendar repetição" }));
    const dialog = await screen.findByRole("dialog", { name: /Repetir Hemoglobina/ });
    await userEvent.click(within(dialog).getByRole("button", { name: "Guardar" }));

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, init]) => init?.method === "POST");
      expect(call?.[0]).toBe("/api/repeats");
      const body = JSON.parse(String(call?.[1]?.body));
      expect(body).toMatchObject({ result_id: "res-1", note: null });
    });
  });
});
