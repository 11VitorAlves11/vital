import type { Meta, StoryObj } from "@storybook/react-vite";

import type { Result } from "../../lib/api/types";
import { ResultRow } from "./ResultRow";

const RESULT: Result = {
  id: "res-1",
  biomarker_id: 1,
  biomarker_slug: "hemoglobina",
  biomarker_name: "Hemoglobina",
  category: "hematologia",
  value: "10.5",
  unit: "g/dL",
  canonical_value: "10.5",
  canonical_unit: "g/dL",
  ref_min: "12",
  ref_max: "15.5",
  reference_kind: "two_sided",
  reference_bands: null,
  band_label: null,
  method: null,
  note: null,
  note_at: null,
  caveats: [],
  flag: "low",
};

const meta = {
  title: "Domain/ResultRow",
  component: ResultRow,
  args: { result: RESULT },
  decorators: [
    (Story) => (
      <div className="max-w-2xl">
        <Story />
      </div>
    ),
  ],
} satisfies Meta<typeof ResultRow>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Low: Story = {};

export const Normal: Story = { args: { result: { ...RESULT, value: "13.4", flag: "normal" } } };

export const High: Story = {
  args: {
    result: {
      ...RESULT,
      biomarker_name: "Colesterol total",
      category: "lipidos",
      value: "218",
      unit: "mg/dL",
      ref_min: null,
      ref_max: "190",
      flag: "high",
    },
  },
};

/** The lab gave no interval and the catalogue has none for this reader. */
export const NoRange: Story = {
  args: { result: { ...RESULT, ref_min: null, ref_max: null, flag: null } },
};

/** A whole report, which is where the tabular figures have to line up. */
export const AsAReport: Story = {
  render: () => (
    <div className="max-w-2xl">
      {[
        { name: "Hemoglobina", value: "10.5", unit: "g/dL", min: "12", max: "15.5", flag: "low" },
        { name: "Ferritina", value: "18", unit: "ng/mL", min: "15", max: "150", flag: "normal" },
        { name: "Colesterol total", value: "218", unit: "mg/dL", min: null, max: "190", flag: "high" },
        { name: "TSH", value: "2.1", unit: "mU/L", min: "0.4", max: "4", flag: "normal" },
      ].map((row, index) => (
        <ResultRow
          key={row.name}
          result={{
            ...RESULT,
            id: `res-${index}`,
            biomarker_id: index + 1,
            biomarker_name: row.name,
            value: row.value,
            unit: row.unit,
            ref_min: row.min,
            ref_max: row.max,
            flag: row.flag as Result["flag"],
          }}
        />
      ))}
    </div>
  ),
};
