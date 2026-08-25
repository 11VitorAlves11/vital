import { screen } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";

import { renderWithProviders, setViewport, usePortuguese } from "../../test/utils";
import { AppShell } from "./AppShell";

beforeAll(async () => {
  await usePortuguese();
});

describe("AppShell", () => {
  it("uses the bottom bar on a phone", () => {
    setViewport("mobile");
    renderWithProviders(
      <AppShell>
        <p>conteúdo</p>
      </AppShell>,
    );
    // One navigation landmark, whichever form it takes.
    const nav = screen.getByRole("navigation", { name: "Navegação principal" });
    expect(nav.className).toContain("fixed");
    expect(screen.getByRole("link", { name: "Início" })).toBeInTheDocument();
  });

  it("uses the sidebar on a desktop", () => {
    setViewport("desktop");
    renderWithProviders(
      <AppShell>
        <p>conteúdo</p>
      </AppShell>,
    );
    const nav = screen.getByRole("navigation", { name: "Navegação principal" });
    expect(nav.className).toContain("w-56");
  });

  it("labels every destination, never an icon on its own", () => {
    setViewport("mobile");
    renderWithProviders(
      <AppShell>
        <p>conteúdo</p>
      </AppShell>,
    );
    for (const label of ["Início", "Análises", "Corpo", "Intervenções", "Perfil"]) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }
  });
});
