import type { Meta, StoryObj } from "@storybook/react-vite";

import { Logo, LogoMark } from "./Logo";

const meta = {
  title: "Brand/Logo",
  component: Logo,
} satisfies Meta<typeof Logo>;

export default meta;
type Story = StoryObj<typeof meta>;

/** The horizontal lockup, as it appears in the sidebar and the mobile header. */
export const Lockup: Story = {};

export const Mark: Story = {
  render: () => <LogoMark className="h-16 w-auto" />,
};

/**
 * The mark holds at 16px, which is the size that actually decides whether a
 * favicon is any good.
 */
export const Sizes: Story = {
  render: () => (
    <div className="flex items-end gap-6">
      {["h-4", "h-6", "h-10", "h-16", "h-24"].map((size) => (
        <LogoMark key={size} className={`${size} w-auto`} />
      ))}
    </div>
  ),
};

/**
 * The mark is painted from `--logo-deep` and `--logo-light`; the crossing is the
 * light stroke with the deep one repainted over it at 35%. Switch the theme in
 * the toolbar — nothing here is hardcoded, so both come from the tokens.
 *
 * The mark belongs on a surface. It is never set on the accent: two blues of
 * the same family leave the deep stroke with nothing to sit against.
 */
export const OnSurfaces: Story = {
  render: () => (
    <div className="flex flex-wrap gap-4">
      <div className="rounded-[var(--radius-lg)] border border-border bg-surface-raised p-6">
        <Logo />
      </div>
      <div className="rounded-[var(--radius-lg)] border border-border bg-surface p-6">
        <Logo />
      </div>
      <div className="rounded-[var(--radius-lg)] border border-border bg-band p-6">
        <Logo />
      </div>
    </div>
  ),
};
