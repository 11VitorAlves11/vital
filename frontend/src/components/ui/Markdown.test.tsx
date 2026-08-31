import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { renderWithProviders } from "../../test/utils";
import { Markdown } from "./Markdown";

describe("Markdown", () => {
  it("renders the emphasis and lists a note is worth writing", () => {
    renderWithProviders(<Markdown>{"Ferritina **a subir**.\n\n- Repetir em março"}</Markdown>);
    expect(screen.getByText("a subir")).toBeInTheDocument();
    expect(screen.getByRole("listitem")).toHaveTextContent("Repetir em março");
  });

  it("shows raw HTML as text rather than running it", () => {
    // A note is health data someone typed, not markup. `rehype-raw` is absent
    // on purpose, so a script tag is characters and never an element.
    const { container } = renderWithProviders(
      <Markdown>{"Valor <script>alert(1)</script> normal"}</Markdown>,
    );
    expect(container.querySelector("script")).toBeNull();
    expect(container.textContent).toContain("<script>");
  });

  it("refuses a javascript: link", () => {
    renderWithProviders(<Markdown>{"[carregar](javascript:alert(1))"}</Markdown>);
    // react-markdown's default url transform allows http, https, mailto and tel
    // and nothing else, so the anchor comes back with no destination at all.
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText("carregar")).toBeInTheDocument();
  });

  it("opens an external link without handing over the opener", () => {
    renderWithProviders(<Markdown>{"[boletim](https://example.org)"}</Markdown>);
    const link = screen.getByRole("link", { name: "boletim" });
    expect(link).toHaveAttribute("href", "https://example.org");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
  });
});
