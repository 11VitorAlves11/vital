import type { Meta, StoryObj } from "@storybook/react-vite";

import type { Intervention } from "../../lib/api/types";
import { TrendChart } from "./TrendChart";

const day = 86_400_000;
const start = Date.UTC(2025, 1, 14);

function series(values: number[], refMin: number | null, refMax: number | null) {
  return values.map((value, index) => ({
    timestamp: start + index * 90 * day,
    value,
    refMin,
    refMax,
  }));
}

const IRON: Intervention = {
  id: "int-1",
  name: "Ferro bisglicinato",
  kind: "suplemento",
  dose: "25 mg/dia",
  started_on: new Date(start + 180 * day).toISOString().slice(0, 10),
  ended_on: null,
  notes: null,
};

const meta = {
  title: "Domain/TrendChart",
  component: TrendChart,
  args: {
    name: "Hemoglobina",
    unit: "g/dL",
    points: series([11.9, 11.4, 10.8, 10.5, 11.6, 12.4], 12, 15.5),
    interventions: [],
  },
  parameters: { layout: "padded" },
} satisfies Meta<typeof TrendChart>;

export default meta;
type Story = StoryObj<typeof meta>;

/** The lab reported a range with every result, so the band is a shaded area. */
export const WithLabRange: Story = {};

/**
 * The signature element under its worst case: the shading measures 1.12:1
 * against the surface, so the limits are also drawn as labelled dashed lines.
 * Without them a reader who cannot tell the shade from the background has no
 * reference range at all.
 */
export const CanonicalRangeOnly: Story = {
  args: {
    points: series([11.9, 11.4, 10.8, 10.5, 11.6, 12.4], null, null),
    canonicalMin: 12,
    canonicalMax: 15.5,
  },
};

export const WithIntervention: Story = {
  args: { interventions: [IRON] },
};

/**
 * Four periods at once. Each label starts where its period does and steps down,
 * or concurrent names print on top of one another and the overlay says nothing.
 */
export const OverlappingInterventions: Story = {
  args: {
    interventions: [
      IRON,
      { ...IRON, id: "int-2", name: "Vitamina C", dose: "500 mg", started_on: "2025-09-01" },
      { ...IRON, id: "int-3", name: "Dieta hipercalórica", kind: "dieta", dose: null, started_on: "2025-10-15" },
      { ...IRON, id: "int-4", name: "Treino de força", kind: "treino", dose: null, started_on: "2025-11-01" },
    ],
  },
};

/** A metric with no clinical reference: the line, and nothing implied around it. */
export const TrendOnly: Story = {
  args: {
    name: "Índice de gordura visceral",
    unit: "",
    points: series([9, 9.5, 10, 9.5, 9, 8.5], null, null),
  },
};

/** Two readings is the least that is still a trend. */
export const TwoPoints: Story = {
  args: { points: series([11.9, 12.4], 12, 15.5) },
};
