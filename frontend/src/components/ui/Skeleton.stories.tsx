import type { Meta, StoryObj } from "@storybook/react-vite";

import { Card } from "./Card";
import { Skeleton } from "./Skeleton";

const meta = {
  title: "UI/Skeleton",
  component: Skeleton,
  decorators: [
    (Story) => (
      <div className="max-w-md">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof Skeleton>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};

export const SingleLine: Story = { args: { lines: 1 } };

/**
 * Shaped like what it replaces. A placeholder of the wrong height moves the
 * page under the reader's cursor the moment the data lands.
 */
export const ShapedLikeACard: Story = {
  render: () => (
    <Card title="Hemoglobina">
      <Skeleton lines={4} label="A carregar a hemoglobina…" />
    </Card>
  ),
};

export const Grid: Story = {
  render: () => (
    <div className="grid grid-cols-2 gap-4">
      {[0, 1, 2, 3].map((index) => (
        <Card key={index}>
          <Skeleton lines={3} />
        </Card>
      ))}
    </div>
  ),
};
