import type { Meta, StoryObj } from "@storybook/react-vite";

import type { Biomarker, DashboardItem } from "../../lib/api/types";
import { BiomarkerCard } from "./BiomarkerCard";

const HAEMOGLOBIN: Biomarker = {
  id: 1,
  slug: "hemoglobina",
  name: "Hemoglobina",
  category: "hematologia",
  unit_default: "g/dL",
  canonical_unit: "g/dL",
  reference_kind: "two_sided",
  ref_min: "12",
  ref_max: "15.5",
  reference_bands: null,
  aliases: ["Hb", "HGB"],
  notes: null,
};

const ITEM: DashboardItem = {
  biomarker: HAEMOGLOBIN,
  value: "10.5",
  unit: "g/dL",
  flag: "low",
  band_label: null,
  collected_on: "2026-02-14",
  lab_name: "Unilabs",
  sparkline: [
    { date: "2024-06-01", value: "11.9" },
    { date: "2025-02-14", value: "11.4" },
    { date: "2025-09-03", value: "10.8" },
    { date: "2026-02-14", value: "10.5" },
  ],
};

const meta = {
  title: "Domain/BiomarkerCard",
  component: BiomarkerCard,
  args: { item: ITEM },
  decorators: [
    (Story) => (
      <div className="max-w-sm">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof BiomarkerCard>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Low: Story = {};

export const Normal: Story = {
  args: { item: { ...ITEM, value: "13.4", flag: "normal" } },
};

export const High: Story = {
  args: {
    item: {
      ...ITEM,
      biomarker: { ...HAEMOGLOBIN, name: "Colesterol total", ref_min: null, ref_max: "190" },
      value: "218",
      unit: "mg/dL",
      flag: "high",
    },
  },
};

/**
 * The reader's sex is unknown, so the catalogue has no range to judge against
 * and the card says so rather than showing an unflagged value as if it were fine.
 */
export const NoReferenceRange: Story = {
  args: {
    item: {
      ...ITEM,
      biomarker: { ...HAEMOGLOBIN, ref_min: null, ref_max: null },
      flag: null,
    },
  },
};

/** A first reading: value and provenance, but nothing yet to draw a trend from. */
export const SingleReading: Story = {
  args: { item: { ...ITEM, sparkline: [{ date: "2026-02-14", value: "10.5" }] } },
};
