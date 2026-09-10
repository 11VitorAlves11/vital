import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { mockApi, renderWithProviders, setViewport, usePortuguese } from "../test/utils";
import { BodyImport } from "./BodyImport";

const METRICS = [
  { id: 1, slug: "weight", name: "Peso", unit: "kg" },
  { id: 2, slug: "body-fat-pct", name: "Gordura corporal", unit: "%" },
];

const PREVIEW = {
  id: "job-1",
  status: "preview",
  filename: "balanca.png",
  provider: "test/model",
  error: null,
  body_scan_id: null,
  created_at: "2026-09-10T07:35:00Z",
  preview: {
    measured_at: "2026-09-10T07:35:00Z",
    device: "Withings Body+",
    results: [
      {
        metric_id: 1,
        metric_slug: "weight",
        metric_name: "Peso",
        expected_unit: "kg",
        source_name: "Weight",
        source_unit: "kg",
        value: "78.4",
        warnings: [],
      },
      {
        metric_id: null,
        metric_slug: null,
        metric_name: null,
        expected_unit: null,
        source_name: "Body score",
        source_unit: null,
        value: "84",
        warnings: ["unmatched"],
      },
    ],
  },
};

beforeAll(async () => {
  await usePortuguese();
  setViewport("desktop");
});

function open(onCreated = vi.fn()) {
  const fetchMock = mockApi([
    { pattern: /\/api\/body\/metrics/, body: METRICS },
    { pattern: /\/api\/body\/extractions\/[^/]+\/confirm/, body: { id: "scan-1" }, status: 201 },
    { pattern: /\/api\/body\/extractions$/, body: PREVIEW, status: 202 },
  ]);
  renderWithProviders(<BodyImport open onOpenChange={vi.fn()} onCreated={onCreated} />);
  return fetchMock;
}

async function uploadImage() {
  const image = new File([new Uint8Array([1, 2, 3])], "balanca.png", { type: "image/png" });
  await userEvent.upload(screen.getByLabelText(/Fotografar ou escolher imagem/), image);
}

describe("BodyImport", () => {
  it("explains local anonymisation before the image is chosen", async () => {
    open();

    expect(await screen.findByText(/dados pessoais são ocultados localmente/i)).toBeInTheDocument();
  });

  it("shows recognised and unmatched readings for human review", async () => {
    open();
    await uploadImage();

    expect(await screen.findByDisplayValue("78.4")).toBeInTheDocument();
    expect(screen.getByText("Weight · kg")).toBeInTheDocument();
    expect(screen.getByText(/Medição não reconhecida/)).toBeInTheDocument();
  });

  it("stores only the rows the reader keeps", async () => {
    const onCreated = vi.fn();
    const fetchMock = open(onCreated);
    await uploadImage();
    await screen.findByDisplayValue("78.4");

    const removeButtons = screen.getAllByRole("button", { name: "Remover valor" });
    await userEvent.click(removeButtons[1]);
    await userEvent.click(screen.getByRole("button", { name: "Confirmar e guardar" }));

    await waitFor(() => expect(onCreated).toHaveBeenCalled());
    const confirmation = fetchMock.mock.calls.find(([url]) =>
      String(url).endsWith("/job-1/confirm"),
    );
    const payload = JSON.parse(String(confirmation?.[1]?.body));
    expect(payload.values).toEqual([{ metric_id: 1, value: 78.4 }]);
    expect(payload.device).toBe("Withings Body+");
  });
});
