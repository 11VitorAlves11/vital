import type { Meta, StoryObj } from "@storybook/react-vite";

import { Button } from "./Button";
import { Card } from "./Card";
import { FlagChip } from "./FlagChip";

const meta = {
  title: "UI/Card",
  component: Card,
  args: {
    children: (
      <p className="text-ink-muted">
        Última colheita a 14 de fevereiro de 2026, no laboratório Unilabs.
      </p>
    ),
  },
  decorators: [
    (Story) => (
      <div className="max-w-md">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof Card>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Plain: Story = {};

export const WithTitle: Story = { args: { title: "Painel marcial" } };

/** The action sits in the header, aligned to the title it belongs to. */
export const WithAction: Story = {
  args: {
    title: "Painel marcial",
    action: <FlagChip flag="low" label="Baixo" />,
  },
};

export const WithFooterAction: Story = {
  args: {
    title: "Hemoglobina",
    children: (
      <div className="flex flex-col gap-4">
        <p className="metric text-3xl text-ink">
          10,5 <span className="text-lg text-ink-muted">g/dL</span>
        </p>
        <Button variant="secondary">Ver histórico</Button>
      </div>
    ),
  },
};
