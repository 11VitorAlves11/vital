import type { Meta, StoryObj } from "@storybook/react-vite";

import { FlagChip } from "./FlagChip";

const meta = {
  title: "UI/FlagChip",
  component: FlagChip,
  args: { flag: "normal", label: "Normal" },
} satisfies Meta<typeof FlagChip>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Normal: Story = {};

export const Low: Story = { args: { flag: "low", label: "Baixo" } };

export const High: Story = { args: { flag: "high", label: "Alto" } };

/** Only body composition has an intermediate class; a lab result never does. */
export const Warn: Story = { args: { flag: "warn", label: "Pré-obesidade" } };

/** A trend-only metric, or a reader whose sex the app does not know. */
export const Unflagged: Story = { args: { flag: null, label: "Sem referência clínica" } };

/**
 * Green against amber measures about 1.0:1. In greyscale, or to a reader with
 * deuteranopia, only the words tell these apart — which is why the chip always
 * carries the band's label and colour only ever reinforces it.
 */
export const EveryState: Story = {
  render: () => (
    <div className="flex flex-wrap gap-2">
      <FlagChip flag="low" label="Baixo" />
      <FlagChip flag="normal" label="Normal" />
      <FlagChip flag="high" label="Alto" />
      <FlagChip flag="warn" label="Pré-obesidade" />
      <FlagChip flag={null} label="Sem referência clínica" />
    </div>
  ),
};
