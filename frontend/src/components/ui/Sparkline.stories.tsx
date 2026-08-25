import type { Meta, StoryObj } from "@storybook/react-vite";

import { Sparkline } from "./Sparkline";

const meta = {
  title: "UI/Sparkline",
  component: Sparkline,
  args: {
    values: [11.9, 11.4, 10.8, 10.5],
    summary: "Hemoglobina, 4 medições, de 11,9 a 10,5 g/dL",
  },
  decorators: [
    (Story) => (
      <div className="max-w-[12rem]">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof Sparkline>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Falling: Story = {};

export const Rising: Story = {
  args: { values: [12, 18, 24, 31], summary: "Ferritina, 4 medições, de 12 a 31 ng/mL" },
};

/** A series that never moves sits on the middle line, not on the floor. */
export const Flat: Story = {
  args: { values: [2.1, 2.1, 2.1, 2.1], summary: "TSH estável em 2,1 mU/L" },
};

export const Long: Story = {
  args: {
    values: [64, 71, 55, 78, 60, 83, 58, 74, 62, 80, 57, 76],
    summary: "Peso, 12 medições ao longo de um ano",
  },
};

/**
 * One reading is not a trend. Drawing a flat stub for it would read as a chart
 * that failed to load, so the component renders nothing at all.
 */
export const TooFewPoints: Story = {
  args: { values: [10.5], summary: "Uma única medição" },
};
