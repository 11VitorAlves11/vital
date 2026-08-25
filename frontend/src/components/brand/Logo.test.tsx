import { screen } from "@testing-library/react";
import { beforeAll, describe, expect, it } from "vitest";

import { renderWithProviders, usePortuguese } from "../../test/utils";
import { Logo, LogoMark } from "./Logo";

beforeAll(async () => {
  await usePortuguese();
});

describe("Logo", () => {
  it("names the product in text, not only in the drawing", () => {
    renderWithProviders(<Logo />);

    expect(screen.getByText("Vital")).toBeInTheDocument();
  });

  it("hides the mark from assistive technology beside the wordmark", () => {
    const { container } = renderWithProviders(<Logo />);

    expect(container.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  });

  it("gives every mark its own clip path", () => {
    // Two lockups on one page sharing a clip id would leave the second mark
    // clipped by whichever definition the document resolved first.
    const { container } = renderWithProviders(
      <>
        <LogoMark />
        <LogoMark />
      </>,
    );

    const ids = [...container.querySelectorAll("clipPath")].map((node) => node.id);
    expect(ids).toHaveLength(2);
    expect(new Set(ids).size).toBe(2);
  });

  it("paints the mark from the theme tokens, never a fixed blue", () => {
    const { container } = renderWithProviders(<LogoMark />);

    // The path inside <clipPath> is a stencil and carries no fill of its own.
    const fills = [...container.querySelectorAll("path[fill], circle[fill]")].map((node) =>
      node.getAttribute("fill"),
    );
    expect(fills).toHaveLength(4);
    for (const fill of fills) expect(fill).toMatch(/^var\(--logo-(deep|light)\)$/);
  });
});
