import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { mockApi, renderWithProviders, usePortuguese } from "../test/utils";
import { ReportCreate } from "./ReportCreate";

const HAEMOGLOBIN = {
  id: 1,
  slug: "hemoglobina",
  name: "Hemoglobina",
  category: "hematologia",
  unit_default: "g/dL",
  canonical_unit: "g/dL",
  reference_kind: "two_sided",
  ref_min: "13.0000",
  ref_max: "17.0000",
  reference_bands: null,
  aliases: ["Hb"],
  notes: null,
};

const LAB = {
  id: "l1",
  name: "Synlab Braga",
  report_count: 4,
  created_at: "2026-01-01T10:00:00Z",
};

const SUGGESTION = {
  biomarker_id: 1,
  unit: "g/dL",
  ref_min: "13.5000",
  ref_max: "17.5000",
  method: "Citometria de fluxo",
  lab_name: "Synlab Braga",
  collected_on: "2026-01-01",
  same_lab: true,
};

beforeAll(async () => {
  await usePortuguese();
});

function render(suggestion: object = SUGGESTION) {
  const fetchMock = mockApi([
    { pattern: /\/api\/biomarkers/, body: [HAEMOGLOBIN] },
    { pattern: /\/api\/labs/, body: [LAB] },
    { pattern: /\/api\/doctors/, body: [] },
    { pattern: /\/api\/reports\/prefill/, body: [suggestion] },
  ]);
  renderWithProviders(<ReportCreate open onOpenChange={vi.fn()} onCreated={vi.fn()} />);
  return fetchMock;
}

describe("ReportCreate", () => {
  it("fills a row from the last reading once a laboratory is recognised", async () => {
    render();
    await userEvent.type(await screen.findByLabelText("Laboratório"), "SYNLAB  braga");
    await userEvent.selectOptions(screen.getByLabelText("Biomarcador"), "1");

    // The acceptance criterion for 4.2: a known value costs the marker, the
    // value and the date. The range and the assay come with it.
    await waitFor(() => expect(screen.getByLabelText("Ref. mín.")).toHaveValue("13.5000"));
    expect(screen.getByLabelText("Ref. máx.")).toHaveValue("17.5000");
    expect(screen.getByLabelText(/Método analítico/)).toHaveValue("Citometria de fluxo");
    // And it says where the suggestion came from, so it can be doubted.
    expect(screen.getByText(/Synlab Braga · 2026-01-01/)).toBeInTheDocument();
  });

  it("never suggests the value itself", async () => {
    render();
    await userEvent.type(await screen.findByLabelText("Laboratório"), "Synlab Braga");
    await userEvent.selectOptions(screen.getByLabelText("Biomarcador"), "1");
    await waitFor(() => expect(screen.getByLabelText("Ref. mín.")).toHaveValue("13.5000"));
    // The one thing that has to be read off the report every time.
    expect(screen.getByLabelText("Valor")).toHaveValue("");
  });

  it("does not overwrite a range someone has already typed", async () => {
    render();
    await userEvent.type(await screen.findByLabelText("Laboratório"), "Synlab Braga");
    await userEvent.type(screen.getByLabelText("Ref. mín."), "12");
    await userEvent.selectOptions(screen.getByLabelText("Biomarcador"), "1");

    await waitFor(() => expect(screen.getByLabelText("Ref. máx.")).toHaveValue("17.5000"));
    expect(screen.getByLabelText("Ref. mín.")).toHaveValue("12");
  });

  it("does not carry a range across from another laboratory", async () => {
    // 1.1's rule, applied to the suggestion: the interval belongs to the lab
    // that issued it. The assay is not lab-specific, so it still comes across.
    render({ ...SUGGESTION, same_lab: false, lab_name: "Unilabs" });
    await userEvent.type(await screen.findByLabelText("Laboratório"), "Laboratório novo");
    await userEvent.selectOptions(screen.getByLabelText("Biomarcador"), "1");

    await waitFor(() =>
      expect(screen.getByLabelText(/Método analítico/)).toHaveValue("Citometria de fluxo"),
    );
    expect(screen.getByLabelText("Ref. mín.")).toHaveValue("");
    expect(screen.getByText(/Unilabs/)).toBeInTheDocument();
  });
});
