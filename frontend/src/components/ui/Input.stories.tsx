import type { Meta, StoryObj } from "@storybook/react-vite";

import { Input } from "./Input";

const meta = {
  title: "UI/Input",
  component: Input,
  args: { label: "Hemoglobina" },
  decorators: [
    (Story) => (
      <div className="max-w-sm">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof Input>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

/** Clinical values arrive with a unit; the field shows it rather than implying it. */
export const WithUnit: Story = {
  args: { unit: "g/dL", inputMode: "decimal", defaultValue: "13.4" },
};

export const WithHint: Story = {
  args: { hint: "O valor tal como vem no boletim, sem arredondar." },
};

/** The message sits under the field that failed, never only in a summary. */
export const WithError: Story = {
  args: { error: "Introduz um número.", defaultValue: "doze" },
};

export const Disabled: Story = { args: { disabled: true, defaultValue: "13.4" } };

export const States: Story = {
  render: () => (
    <div className="flex flex-col gap-4">
      <Input label="Normal" defaultValue="13.4" unit="g/dL" />
      <Input label="Com pista" hint="Como vem no boletim." />
      <Input label="Com erro" error="Introduz um número." defaultValue="doze" />
      <Input label="Desativado" disabled defaultValue="13.4" />
    </div>
  ),
};
