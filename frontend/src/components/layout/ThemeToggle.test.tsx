import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeAll, describe, expect, it } from "vitest";

import { renderWithProviders, setViewport, usePortuguese } from "../../test/utils";
import { ThemeToggle } from "./ThemeToggle";

beforeAll(async () => {
  await usePortuguese();
});

afterEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute("data-theme");
});

describe("ThemeToggle", () => {
  it("does not store the system-derived theme as an explicit preference", () => {
    setViewport("mobile");

    renderWithProviders(<ThemeToggle />);

    expect(document.documentElement).toHaveAttribute("data-theme", "light");
    expect(localStorage.getItem("vital-theme")).toBeNull();
  });

  it("applies and stores an explicit dark theme", async () => {
    setViewport("mobile");
    const user = userEvent.setup();
    renderWithProviders(<ThemeToggle />);

    await user.click(screen.getByRole("button", { name: "Ativar tema escuro" }));

    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
    expect(localStorage.getItem("vital-theme")).toBe("dark");
    expect(screen.getByRole("button", { name: "Ativar tema claro" })).toBeInTheDocument();
  });

  it("restores the stored preference", () => {
    setViewport("mobile");
    localStorage.setItem("vital-theme", "dark");

    renderWithProviders(<ThemeToggle />);

    expect(document.documentElement).toHaveAttribute("data-theme", "dark");
    expect(screen.getByRole("button", { name: "Ativar tema claro" })).toBeInTheDocument();
  });
});
