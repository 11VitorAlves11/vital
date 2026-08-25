import type { Meta, StoryObj } from "@storybook/react-vite";

import { Tabs } from "./Tabs";

const meta = {
  title: "UI/Tabs",
  component: Tabs,
  args: {
    "aria-label": "Categorias de biomarcadores",
    items: [
      { value: "hematologia", label: "Hematologia", content: <p>Hemograma e painel marcial.</p> },
      { value: "lipidos", label: "Lípidos", content: <p>Colesterol total, HDL, LDL.</p> },
      { value: "vitaminas", label: "Vitaminas", content: <p>Vitamina D, B12, folato.</p> },
    ],
  },
} satisfies Meta<typeof Tabs>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const SecondSelected: Story = { args: { defaultValue: "lipidos" } };

/**
 * Nine categories do not fit a phone. The list scrolls sideways rather than
 * wrapping into rows that push the panel off the screen.
 */
export const Overflowing: Story = {
  args: {
    items: [
      "Hematologia",
      "Bioquímica",
      "Vitaminas",
      "Ferro",
      "Hormonas",
      "Lípidos",
      "Renal",
      "Hepático",
      "Outro",
    ].map((label) => ({
      value: label.toLowerCase(),
      label,
      content: <p>{label}</p>,
    })),
  },
  decorators: [
    (Story) => (
      <div className="max-w-xs">
        <Story />
      </div>
    ),
  ],
};
