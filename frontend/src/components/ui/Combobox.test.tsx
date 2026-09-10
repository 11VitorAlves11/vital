import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";

import { renderWithProviders } from "../../test/utils";
import { Combobox } from "./Combobox";

const options = [
  { value: "3", label: "Vitamina B12 (pg/mL)" },
  { value: "2", label: "Basófilos (%) (%)" },
  { value: "1", label: "Basófilos (10^9/L)" },
  { value: "4", label: "Ácido fólico (ng/mL)" },
];

it("orders biomarker options alphabetically and filters them by name prefix", async () => {
  const onValueChange = vi.fn();
  renderWithProviders(
    <Combobox
      label="Biomarcador"
      options={options}
      value=""
      onValueChange={onValueChange}
      placeholder="Escolher biomarcador"
      noResults="Nenhum biomarcador começa por esse texto."
    />,
  );

  const input = screen.getByRole("combobox", { name: "Biomarcador" });
  await userEvent.click(input);
  expect(screen.getAllByRole("option").map((option) => option.textContent)).toEqual([
    "Ácido fólico (ng/mL)",
    "Basófilos (%) (%)",
    "Basófilos (10^9/L)",
    "Vitamina B12 (pg/mL)",
  ]);

  await userEvent.type(input, "baso");
  expect(screen.getAllByRole("option")).toHaveLength(2);
  expect(screen.queryByText("Vitamina B12 (pg/mL)")).not.toBeInTheDocument();

  await userEvent.keyboard("{ArrowDown}{Enter}");
  expect(onValueChange).toHaveBeenCalledWith("1");
});

it("explains when no biomarker starts with the entered text", async () => {
  renderWithProviders(
    <Combobox
      label="Biomarcador"
      options={options}
      value=""
      onValueChange={() => {}}
      noResults="Nenhum biomarcador começa por esse texto."
    />,
  );

  await userEvent.type(screen.getByRole("combobox"), "zzzz");
  expect(screen.getByText("Nenhum biomarcador começa por esse texto.")).toBeInTheDocument();
});
