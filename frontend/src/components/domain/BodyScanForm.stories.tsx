import type { Decorator, Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";

import type { BodyMetric } from "../../lib/api/types";
import { Button } from "../ui/Button";
import { BodyScanForm } from "./BodyScanForm";

const METRICS: BodyMetric[] = [
  { slug: "weight", name: "Peso", unit: "kg", bands: null },
  {
    slug: "bmi",
    name: "IMC (índice de massa corporal)",
    unit: "kg/m²",
    bands: [
      { label: "Baixo peso", min: null, max: 18.5, flag: "warn" },
      { label: "Normal", min: 18.5, max: 25, flag: "normal" },
      { label: "Pré-obesidade", min: 25, max: 30, flag: "warn" },
      { label: "Obesidade", min: 30, max: null, flag: "alert" },
    ],
  },
  { slug: "body-fat-pct", name: "Massa gorda", unit: "%", bands: null },
  { slug: "fat-mass", name: "Massa gorda (absoluta)", unit: "kg", bands: null },
  { slug: "subcutaneous-fat-pct", name: "Gordura subcutânea", unit: "%", bands: null },
  { slug: "visceral-fat-index", name: "Índice de gordura visceral", unit: "", bands: null },
  { slug: "waist-circumference", name: "Perímetro abdominal", unit: "cm", bands: null },
  { slug: "muscle-mass", name: "Massa muscular", unit: "kg", bands: null },
  { slug: "bone-mass", name: "Massa óssea", unit: "kg", bands: null },
  { slug: "body-water-pct", name: "Água corporal", unit: "%", bands: null },
  { slug: "protein-pct", name: "Proteína", unit: "%", bands: null },
  { slug: "bmr", name: "Metabolismo basal", unit: "kcal", bands: null },
  { slug: "metabolic-age", name: "Idade metabólica", unit: "anos", bands: null },
].map((metric, index) => ({
  ...metric,
  id: index + 1,
  source: null,
  notes: null,
})) as BodyMetric[];

/**
 * The form reads the catalogue from the API. A story is not the place to run a
 * server, so the catalogue is answered from a fixture and the POST is accepted
 * without one.
 */
const withStubbedCatalogue: Decorator = (Story) => {
  window.fetch = (async (input: RequestInfo | URL) => {
    const url = String(input);
    const body = url.includes("/api/body/metrics") ? METRICS : { ok: true };
    return new Response(JSON.stringify(body), {
      status: 200,
      headers: { "content-type": "application/json" },
    });
  }) as typeof window.fetch;
  return <Story />;
};

function Demo() {
  const [open, setOpen] = useState(true);
  return (
    <>
      <Button onClick={() => setOpen(true)}>Registar pesagem</Button>
      <BodyScanForm open={open} onOpenChange={setOpen} onCreated={() => {}} />
    </>
  );
}

const meta = {
  title: "Domain/BodyScanForm",
  component: BodyScanForm,
  args: { open: true, onOpenChange: () => {}, onCreated: () => {} },
  decorators: [withStubbedCatalogue],
} satisfies Meta<typeof BodyScanForm>;

export default meta;
type Story = StoryObj<typeof meta>;

/**
 * Eighteen figures copied off a scale app in one sitting. Ungrouped that is a
 * wall; grouped the way the scale reports them it is five short lists.
 */
export const Open: Story = { render: () => <Demo /> };

/** Desktop width: the fields pair up, and the groups stay the unit of reading. */
export const Desktop: Story = {
  render: () => <Demo />,
  parameters: { viewport: { defaultViewport: "desktop" } },
};
