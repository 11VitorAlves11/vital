import type { Meta, StoryObj } from "@storybook/react-vite";
import { FlaskConical } from "lucide-react";

import { Button } from "./Button";
import { EmptyState } from "./EmptyState";

const meta = {
  title: "UI/EmptyState",
  component: EmptyState,
  args: { title: "Ainda não há análises" },
} satisfies Meta<typeof EmptyState>;

export default meta;
type Story = StoryObj<typeof meta>;

/** Bare title only: the state exists, but it leads the reader nowhere. */
export const TitleOnly: Story = {};

/**
 * The pattern the app actually uses. "Sem dados" is a dead end; the next action
 * spelled out is the whole point of the component.
 */
export const WithNextAction: Story = {
  args: {
    icon: <FlaskConical size={28} className="text-ink-muted" aria-hidden="true" />,
    description: "Regista a primeira colheita para começar a ver tendências.",
    action: <Button>Registar colheita</Button>,
  },
};

export const Filtered: Story = {
  args: {
    title: "Nenhuma análise neste período",
    description: "Alarga o intervalo de datas ou limpa os filtros.",
    action: <Button variant="secondary">Limpar filtros</Button>,
  },
};
