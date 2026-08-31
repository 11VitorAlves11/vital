import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it } from "vitest";

import { mockApi, renderWithProviders, usePortuguese } from "../test/utils";
import { Timeline } from "./Timeline";

const REPORT = {
  id: "lab_report:r1",
  kind: "lab_report",
  occurred_on: "2026-03-01",
  occurred_at: "2026-03-01T08:15:00",
  ended_on: null,
  has_duration: false,
  title: "Synlab Braga",
  subtitle: "Dra. Sofia Nunes",
  summary: [{ label: "Hemoglobina", value: "11 g/dL", flag: "low" }],
  href: "/reports/r1",
  intervention_kind: null,
  pose: null,
  photo_id: null,
};

const SUPPLEMENT = {
  id: "intervention:i1",
  kind: "intervention",
  occurred_on: "2025-10-01",
  occurred_at: null,
  ended_on: null,
  has_duration: true,
  title: "Vitamina D",
  subtitle: "2000 UI/dia",
  summary: [],
  href: "/interventions",
  intervention_kind: "suplemento",
  pose: null,
  photo_id: null,
};

beforeAll(async () => {
  await usePortuguese();
});

function render(body: object) {
  const fetchMock = mockApi([{ pattern: /\/api\/timeline/, body }]);
  renderWithProviders(<Timeline />, { route: "/timeline" });
  return fetchMock;
}

const FULL = {
  events: [REPORT, SUPPLEMENT],
  available_kinds: ["lab_report", "intervention"],
  next_before: null,
};

describe("Timeline", () => {
  it("groups events under the year and month they fall in", async () => {
    render(FULL);
    expect(await screen.findByRole("heading", { name: "2026" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "2025" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "março" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "outubro" })).toBeInTheDocument();
  });

  it("shows the hour on a draw and not on a supplement", async () => {
    render(FULL);
    // The hour changes how a blood value reads; a supplement did not start at one.
    expect(await screen.findByText(/08:15/)).toBeInTheDocument();
    expect(screen.getByText(/em curso/)).toBeInTheDocument();
  });

  it("expands a card in place rather than navigating away", async () => {
    render(FULL);
    await userEvent.click((await screen.findAllByRole("button", { name: "Ver detalhe" }))[0]);
    // The summary appears without leaving the list.
    expect(screen.getByText("Hemoglobina")).toBeInTheDocument();
    expect(screen.getByText("11 g/dL")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "2026" })).toBeInTheDocument();
  });

  it("filters by kind and asks the server for it", async () => {
    const fetchMock = render(FULL);
    const filter = await screen.findByRole("group", { name: "Filtrar por tipo" });
    await userEvent.click(within(filter).getByRole("button", { name: "Intervenção" }));

    await waitFor(() => {
      const urls = fetchMock.mock.calls.map(([input]) => String(input));
      expect(urls.some((url) => url.includes("kinds=intervention"))).toBe(true);
    });
  });

  it("offers no filter when there is only one kind of thing to see", async () => {
    render({ events: [REPORT], available_kinds: ["lab_report"], next_before: null });
    await screen.findByText("Synlab Braga");
    expect(screen.queryByRole("group", { name: "Filtrar por tipo" })).not.toBeInTheDocument();
  });

  it("offers more only while the history has more", async () => {
    render(FULL);
    await screen.findByText("Synlab Braga");
    expect(screen.queryByRole("button", { name: "Carregar mais" })).not.toBeInTheDocument();
  });
});
