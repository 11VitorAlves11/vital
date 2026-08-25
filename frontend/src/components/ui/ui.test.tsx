import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { renderWithProviders, usePortuguese } from "../../test/utils";
import { Button } from "./Button";
import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
import { FlagChip } from "./FlagChip";
import { Input } from "./Input";
import { Select } from "./Select";
import { Skeleton } from "./Skeleton";
import { Sparkline } from "./Sparkline";
import { Tabs } from "./Tabs";

beforeAll(async () => {
  await usePortuguese();
});

describe("Button", () => {
  it("is a real button and reports its busy state", async () => {
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Guardar
      </Button>,
    );
    const button = screen.getByRole("button", { name: "Guardar" });
    expect(button).toHaveAttribute("aria-busy", "true");
    expect(button).toBeDisabled();
    await userEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("uses the on-primary token rather than a hardcoded white", () => {
    render(<Button>Guardar</Button>);
    expect(screen.getByRole("button").className).toContain("text-on-primary");
  });
});

describe("Input", () => {
  it("always has a visible label tied to the field", () => {
    render(<Input label="Hemoglobina" unit="g/dL" />);
    expect(screen.getByLabelText("Hemoglobina")).toBeInTheDocument();
    expect(screen.getByText("g/dL")).toBeInTheDocument();
  });

  it("announces the error next to the field", () => {
    render(<Input label="Valor" error="Campo obrigatório." />);
    const field = screen.getByLabelText("Valor");
    expect(field).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByRole("alert")).toHaveTextContent("Campo obrigatório.");
    expect(field.getAttribute("aria-describedby")).toBe(screen.getByRole("alert").id);
  });

  it("draws its border from the informative token, not the decorative one", () => {
    render(<Input label="Valor" />);
    expect(screen.getByLabelText("Valor").className).toContain("border-border-strong");
  });
});

describe("Select", () => {
  it("labels the control and lists its options", async () => {
    render(
      <Select
        label="Sexo"
        placeholder="Não indicado"
        options={[
          { value: "M", label: "Masculino" },
          { value: "F", label: "Feminino" },
        ]}
      />,
    );
    const select = screen.getByLabelText("Sexo");
    await userEvent.selectOptions(select, "F");
    expect(select).toHaveValue("F");
    expect(screen.getByRole("option", { name: "Não indicado" })).toBeInTheDocument();
  });
});

describe("FlagChip", () => {
  it.each([
    ["normal", "Normal", "text-flag-normal"],
    ["warn", "Pré-obesidade", "text-flag-warn"],
    ["high", "Alto", "text-flag-alert"],
    ["low", "Baixo", "text-flag-alert"],
  ])("renders %s with its label and tone", (flag, label, tone) => {
    const { container } = render(
      <FlagChip flag={flag as "normal" | "warn" | "high" | "low"} label={label} />,
    );
    // The label is the signal; the colour only reinforces it.
    expect(screen.getByText(label)).toBeInTheDocument();
    expect(container.firstElementChild?.className).toContain(tone);
  });

  it("falls back to a muted chip when there is nothing to classify against", () => {
    const { container } = render(<FlagChip flag={null} label="Sem classificação" />);
    expect(container.firstElementChild?.className).toContain("text-ink-muted");
  });
});

describe("Sparkline", () => {
  it("is an image with a text alternative", () => {
    render(<Sparkline values={[1, 2, 3]} summary="Últimos 3 valores" />);
    expect(screen.getByRole("img", { name: "Últimos 3 valores" })).toBeInTheDocument();
  });

  it("renders nothing without data instead of an empty axis", () => {
    const { container } = render(<Sparkline values={[]} summary="vazio" />);
    expect(container).toBeEmptyDOMElement();
  });
});

describe("Skeleton", () => {
  it("marks the region busy while it stands in for content", () => {
    render(<Skeleton lines={2} label="A carregar…" />);
    const region = screen.getByText("A carregar…").parentElement;
    expect(region).toHaveAttribute("aria-busy", "true");
  });
});

describe("EmptyState", () => {
  it("spells out the next action", () => {
    render(
      <EmptyState
        title="Sem colheitas"
        description="Regista a primeira análise."
        action={<Button>Registar</Button>}
      />,
    );
    expect(screen.getByRole("heading", { name: "Sem colheitas" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Registar" })).toBeInTheDocument();
  });
});

describe("ErrorState", () => {
  it("stays next to the content and offers a retry", async () => {
    const onRetry = vi.fn();
    renderWithProviders(<ErrorState onRetry={onRetry} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Tentar novamente" }));
    expect(onRetry).toHaveBeenCalledOnce();
  });
});

describe("Tabs", () => {
  it("switches panels on selection", async () => {
    render(
      <Tabs
        aria-label="Secções"
        items={[
          { value: "a", label: "Primeira", content: <p>Conteúdo A</p> },
          { value: "b", label: "Segunda", content: <p>Conteúdo B</p> },
        ]}
      />,
    );
    expect(screen.getByText("Conteúdo A")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: "Segunda" }));
    expect(screen.getByText("Conteúdo B")).toBeInTheDocument();
  });
});
