import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";

import { Button } from "./Button";
import { Dialog } from "./Dialog";
import { Input } from "./Input";

function Demo({ description }: { description?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button onClick={() => setOpen(true)}>Registar colheita</Button>
      <Dialog
        open={open}
        onOpenChange={setOpen}
        title="Registar colheita"
        description={description}
        footer={
          <>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Cancelar
            </Button>
            <Button onClick={() => setOpen(false)}>Guardar</Button>
          </>
        }
      >
        <div className="flex flex-col gap-4">
          <Input label="Data da colheita" type="date" defaultValue="2026-02-14" />
          <Input label="Laboratório" defaultValue="Unilabs" />
          <Input label="Hemoglobina" unit="g/dL" inputMode="decimal" defaultValue="10.5" />
        </div>
      </Dialog>
    </>
  );
}

const meta = {
  title: "UI/Dialog",
  component: Dialog,
  args: { open: false, onOpenChange: () => {}, title: "Registar colheita", children: null },
} satisfies Meta<typeof Dialog>;

export default meta;
type Story = StoryObj<typeof meta>;

/** The desktop surface. Under md the same form is shown as a {@link Sheet}. */
export const Default: Story = { render: () => <Demo /> };

export const WithDescription: Story = {
  render: () => <Demo description="Os valores ficam associados a esta data de colheita." />,
};

export const OpenOnLoad: Story = {
  render: () => (
    <Dialog open onOpenChange={() => {}} title="Apagar esta análise?">
      <p className="text-ink-muted">Os resultados desta colheita são apagados com ela.</p>
    </Dialog>
  ),
};
