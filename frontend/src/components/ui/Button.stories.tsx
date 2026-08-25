import type { Meta, StoryObj } from "@storybook/react-vite";
import { Plus } from "lucide-react";

import { Button } from "./Button";

const meta = {
  title: "UI/Button",
  component: Button,
  args: { children: "Registar colheita" },
} satisfies Meta<typeof Button>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Primary: Story = {};

export const Secondary: Story = { args: { variant: "secondary" } };

export const Ghost: Story = { args: { variant: "ghost" } };

/** Destructive actions carry the alert colour on the border, not on the fill. */
export const Danger: Story = { args: { variant: "danger", children: "Apagar análise" } };

export const WithIcon: Story = {
  args: { icon: <Plus size={18} aria-hidden="true" /> },
};

export const Loading: Story = { args: { loading: true, children: "A guardar…" } };

export const Disabled: Story = { args: { disabled: true } };

/** Every variant beside every other, which is the only way to see them drift. */
export const AllVariants: Story = {
  render: () => (
    <div className="flex flex-wrap items-center gap-3">
      <Button>Primária</Button>
      <Button variant="secondary">Secundária</Button>
      <Button variant="ghost">Fantasma</Button>
      <Button variant="danger">Perigosa</Button>
      <Button loading>A guardar…</Button>
      <Button disabled>Desativada</Button>
    </div>
  ),
};
