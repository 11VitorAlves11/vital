import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

import { mockApi, renderWithProviders, setViewport, usePortuguese } from "../test/utils";
import { ReportImport } from "./ReportImport";

const HAEMOGLOBIN = {
  id: 1,
  slug: "hemoglobina",
  name: "Hemoglobina",
  category: "hematologia",
  unit_default: "g/dL",
  ref_min: "12",
  ref_max: "15.5",
  aliases: [],
  notes: null,
};

const PREVIEW = {
  id: "job-1",
  status: "preview",
  filename: "analises.pdf",
  provider: "test/model",
  error: null,
  report_id: null,
  created_at: "2026-02-14T10:00:00Z",
  preview: {
    collected_on: "2026-02-14",
    lab_name: "Unilabs",
    collected_at: "2026-02-14T08:15:00",
    fasting_state: "fasting",
    results: [
      {
        biomarker_id: 1,
        biomarker_name: "Hemoglobina",
        biomarker_slug: "hemoglobina",
        source_name: "HEMOGLOBINA",
        value: "10.5",
        unit: "g/dL",
        ref_min: "12",
        ref_max: "15.5",
      },
      {
        biomarker_id: null,
        biomarker_name: null,
        biomarker_slug: null,
        source_name: "Marcador Desconhecido",
        value: "1.2",
        unit: null,
        ref_min: null,
        ref_max: null,
      },
    ],
  },
};

beforeAll(async () => {
  await usePortuguese();
  setViewport("desktop");
});

afterEach(() => {
  vi.restoreAllMocks();
});

function open(job: unknown = PREVIEW, onCreated = vi.fn()) {
  const fetchMock = mockApi([
    { pattern: /\/api\/biomarkers/, body: [HAEMOGLOBIN] },
    { pattern: /\/api\/extractions\/[^/]+\/confirm/, body: { id: "r1" }, status: 201 },
    { pattern: /\/api\/extractions/, body: job, status: 202 },
  ]);
  renderWithProviders(<ReportImport open onOpenChange={vi.fn()} onCreated={onCreated} />);
  return fetchMock;
}

async function uploadPdf() {
  const file = new File([new Uint8Array([0x25, 0x50, 0x44, 0x46])], "analises.pdf", {
    type: "application/pdf",
  });
  await userEvent.upload(screen.getByLabelText(/Escolher ou fotografar o boletim/), file);
}

describe("ReportImport", () => {
  it("says up front that nothing is stored before confirmation", async () => {
    open();

    expect(
      await screen.findByText(/nada é guardado no histórico antes de confirmares/),
    ).toBeInTheDocument();
  });

  it("shows every read line as an editable row", async () => {
    open();

    await uploadPdf();

    expect(await screen.findByDisplayValue("10.5")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Unilabs")).toBeInTheDocument();
    expect(screen.getByDisplayValue("2026-02-14")).toBeInTheDocument();
  });

  it("keeps what the document called each line, beside the match", async () => {
    open();

    await uploadPdf();

    // A wrong match has to be visible without opening the PDF next to it.
    expect(await screen.findByText("HEMOGLOBINA")).toBeInTheDocument();
    expect(screen.getByText("Marcador Desconhecido")).toBeInTheDocument();
  });

  it("shows an unmatched line rather than dropping it, and says how many", async () => {
    open();

    await uploadPdf();

    expect(
      await screen.findByText(/1 linha não corresponde a nenhum biomarcador/),
    ).toBeInTheDocument();
  });

  it("sends only the rows that have a biomarker and a value", async () => {
    const onCreated = vi.fn();
    const fetchMock = open(PREVIEW, onCreated);
    await uploadPdf();
    await screen.findByDisplayValue("10.5");

    await userEvent.click(screen.getByRole("button", { name: "Confirmar e guardar" }));

    await waitFor(() => expect(onCreated).toHaveBeenCalled());
    const confirm = fetchMock.mock.calls.find(([url]) => String(url).endsWith("/confirm"));
    const body = JSON.parse(String((confirm?.[1] as RequestInit).body));
    // The unmatched second row carried a value but no biomarker: it is dropped.
    expect(body.results).toHaveLength(1);
    expect(body.results[0]).toMatchObject({ biomarker_id: 1, value: 10.5 });
  });

  it("saves the reader's correction, not what the model read", async () => {
    const fetchMock = open();
    await uploadPdf();
    const value = await screen.findByDisplayValue("10.5");

    await userEvent.clear(value);
    await userEvent.type(value, "10,9");
    await userEvent.click(screen.getByRole("button", { name: "Confirmar e guardar" }));

    await waitFor(() => {
      const confirm = fetchMock.mock.calls.find(([url]) => String(url).endsWith("/confirm"));
      expect(confirm).toBeDefined();
      const body = JSON.parse(String((confirm?.[1] as RequestInit).body));
      expect(body.results[0].value).toBe(10.9);
    });
  });

  it("reports a failed extraction in its own words, with a way out", async () => {
    open({ ...PREVIEW, status: "failed", error: "O modelo não respondeu em JSON.", preview: null });

    await uploadPdf();

    expect(await screen.findByRole("alert")).toHaveTextContent("O modelo não respondeu em JSON.");
    expect(screen.getByRole("button", { name: "Tentar outro ficheiro" })).toBeInTheDocument();
  });

  it("shows progress while the model is still reading", async () => {
    open({ ...PREVIEW, status: "processing", preview: null });

    await uploadPdf();

    expect(await screen.findByText(/A ler o boletim/)).toBeInTheDocument();
  });
});
