import type { Meta, StoryObj } from "@storybook/react-vite";

import { Select } from "./Select";

const BIOMARKERS = [
  { value: "hemoglobina", label: "Hemoglobina" },
  { value: "ferritina", label: "Ferritina" },
  { value: "vitamina-d", label: "Vitamina D (25-OH)" },
  { value: "tsh", label: "TSH" },
];

const meta = {
  title: "UI/Select",
  component: Select,
  args: { label: "Biomarcador", options: BIOMARKERS },
  decorators: [
    (Story) => (
      <div className="max-w-sm">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof Select>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

/** An unset value is a real option, not a blank first row with no meaning. */
export const WithPlaceholder: Story = { args: { placeholder: "Escolher…" } };

export const WithError: Story = { args: { error: "Escolhe um biomarcador." } };

export const Disabled: Story = { args: { disabled: true } };
