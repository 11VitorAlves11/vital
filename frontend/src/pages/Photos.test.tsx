import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it } from "vitest";

import { mockApi, renderWithProviders, setViewport, usePortuguese } from "../test/utils";
import { Photos } from "./Photos";

const PHOTOS = [
  {
    id: "p2",
    taken_on: "2026-02-14",
    pose: "frente",
    width: 600,
    height: 900,
    notes: null,
    created_at: "2026-02-14T10:00:00Z",
  },
  {
    id: "p1",
    taken_on: "2025-11-01",
    pose: "frente",
    width: 600,
    height: 900,
    notes: "Início do ciclo",
    created_at: "2025-11-01T10:00:00Z",
  },
];

beforeAll(async () => {
  await usePortuguese();
  setViewport("desktop");
});

describe("Photos", () => {
  it("says what happens to the metadata before anything is uploaded", async () => {
    mockApi([{ pattern: /\/api\/photos/, body: PHOTOS }]);

    renderWithProviders(<Photos />);

    expect(
      await screen.findByText(/a localização, o modelo da câmara e a hora de captura/i),
    ).toBeInTheDocument();
  });

  it("describes each photo by pose and date, not as 'image'", async () => {
    mockApi([{ pattern: /\/api\/photos/, body: PHOTOS }]);

    renderWithProviders(<Photos />);

    expect(
      await screen.findByAltText("Foto de progresso, pose Frente, de 14/02/2026"),
    ).toBeInTheDocument();
  });

  it("reserves each image's box from the stored dimensions", async () => {
    mockApi([{ pattern: /\/api\/photos/, body: PHOTOS }]);

    renderWithProviders(<Photos />);

    const image = await screen.findByAltText("Foto de progresso, pose Frente, de 14/02/2026");
    expect(image).toHaveAttribute("width", "600");
    expect(image).toHaveAttribute("height", "900");
  });

  it("serves every photo through the authenticated endpoint", async () => {
    mockApi([{ pattern: /\/api\/photos/, body: PHOTOS }]);

    renderWithProviders(<Photos />);

    const image = await screen.findByAltText("Foto de progresso, pose Frente, de 14/02/2026");
    expect(image).toHaveAttribute("src", "/api/photos/p2/file");
  });

  it("compares two photos and says how far apart they are", async () => {
    mockApi([{ pattern: /\/api\/photos/, body: PHOTOS }]);
    renderWithProviders(<Photos />);
    await screen.findByAltText("Foto de progresso, pose Frente, de 14/02/2026");

    await userEvent.click(screen.getByRole("tab", { name: "Comparar" }));

    const panel = screen.getByRole("tabpanel");
    expect(within(panel).getByText("105 dias de intervalo")).toBeInTheDocument();
  });

  it("announces the date a slider landed on, never the index", async () => {
    mockApi([{ pattern: /\/api\/photos/, body: PHOTOS }]);
    renderWithProviders(<Photos />);
    await screen.findByAltText("Foto de progresso, pose Frente, de 14/02/2026");

    await userEvent.click(screen.getByRole("tab", { name: "Comparar" }));

    // "1 of 2" would tell a screen-reader user nothing about the comparison.
    expect(screen.getByLabelText("Primeira foto")).toHaveAttribute(
      "aria-valuetext",
      "01/11/2025",
    );
  });

  it("asks for a second photo instead of comparing one with itself", async () => {
    mockApi([{ pattern: /\/api\/photos/, body: [PHOTOS[0]] }]);
    renderWithProviders(<Photos />);
    await screen.findByAltText("Foto de progresso, pose Frente, de 14/02/2026");

    await userEvent.click(screen.getByRole("tab", { name: "Comparar" }));

    expect(screen.getByText("Faltam fotos para comparar")).toBeInTheDocument();
  });

  it("offers the next action when there is nothing yet", async () => {
    mockApi([{ pattern: /\/api\/photos/, body: [] }]);

    renderWithProviders(<Photos />);

    expect(await screen.findByText("Ainda não há fotos")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "Adicionar foto" }).length).toBeGreaterThan(0);
  });

  it("filters by pose", async () => {
    const fetchMock = mockApi([{ pattern: /\/api\/photos/, body: PHOTOS }]);
    renderWithProviders(<Photos />);
    await screen.findByAltText("Foto de progresso, pose Frente, de 14/02/2026");

    await userEvent.selectOptions(screen.getByLabelText("Pose"), "lado");

    expect(
      fetchMock.mock.calls.some(([url]) => String(url).includes("pose=lado")),
    ).toBe(true);
  });
});
