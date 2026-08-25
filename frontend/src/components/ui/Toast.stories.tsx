import type { Meta, StoryObj } from "@storybook/react-vite";

import { Button } from "./Button";
import { ToastProvider, useToast } from "./Toast";

/**
 * The preview already wraps every story in a ToastProvider, so these stories
 * only need something that calls `useToast`.
 */
function Trigger({ title, tone }: { title: string; tone?: "success" | "error" }) {
  const notify = useToast();
  return <Button onClick={() => notify(title, tone)}>Mostrar mensagem</Button>;
}

const meta = {
  title: "UI/Toast",
  component: ToastProvider,
  args: { children: null },
} satisfies Meta<typeof ToastProvider>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Confirmation: Story = {
  render: () => <Trigger title="Perfil guardado." />,
};

/**
 * Errors live beside the thing that failed. A toast is only ever the receipt
 * for something that already worked — this one exists so the tone is testable,
 * not as a licence to report failures here.
 */
export const ErrorTone: Story = {
  render: () => <Trigger title="Não foi possível guardar." tone="error" />,
};

export const Stacked: Story = {
  render: function Stacked() {
    const notify = useToast();
    return (
      <Button
        onClick={() => {
          notify("Colheita registada.");
          notify("Pesagem registada.");
          notify("Intervenção terminada.");
        }}
      >
        Três de uma vez
      </Button>
    );
  },
};
