import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";

import { Button } from "./Button";
import { Input } from "./Input";
import { Sheet } from "./Sheet";

function Demo() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button onClick={() => setOpen(true)}>Registar pesagem</Button>
      <Sheet
        open={open}
        onOpenChange={setOpen}
        title="Registar pesagem"
        description="Copia os valores da app da balança."
        footer={<Button onClick={() => setOpen(false)}>Guardar</Button>}
      >
        <div className="flex flex-col gap-4">
          <Input label="Peso" unit="kg" inputMode="decimal" defaultValue="74.2" />
          <Input label="Massa gorda" unit="%" inputMode="decimal" defaultValue="27.4" />
        </div>
      </Sheet>
    </>
  );
}

const meta = {
  title: "UI/Sheet",
  component: Sheet,
  args: { open: false, onOpenChange: () => {}, title: "Registar pesagem", children: null },
  parameters: {
    // The sheet is the mobile surface; judging it at desktop width is judging
    // the wrong thing.
    viewport: { defaultViewport: "mobile1" },
  },
} satisfies Meta<typeof Sheet>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = { render: () => <Demo /> };

export const OpenOnLoad: Story = {
  render: () => (
    <Sheet open onOpenChange={() => {}} title="Registar pesagem">
      <Input label="Peso" unit="kg" inputMode="decimal" defaultValue="74.2" />
    </Sheet>
  ),
};
