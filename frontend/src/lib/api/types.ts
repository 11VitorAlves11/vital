/** Mirrors the response models in backend/app/schemas. */

export type Sex = "M" | "F";
export type ResultFlag = "low" | "normal" | "high";
export type BandFlag = "normal" | "warn" | "alert";

export type BiomarkerCategory =
  | "hematologia"
  | "bioquimica"
  | "vitaminas"
  | "ferro"
  | "hormonas"
  | "lipidos"
  | "renal"
  | "hepatico"
  | "outro";

export type InterventionKind = "suplemento" | "medicacao" | "dieta" | "treino" | "outro";

export type User = {
  id: string;
  email: string | null;
  name: string | null;
  sex: Sex | null;
  birth_date: string | null;
  created_at: string;
};

export type Band = {
  label: string;
  min: number | null;
  max: number | null;
  flag: BandFlag;
};

export type Biomarker = {
  id: number;
  slug: string;
  name: string;
  category: BiomarkerCategory;
  unit_default: string;
  /** Canonical range for the caller's sex; null when their sex is unknown. */
  ref_min: string | null;
  ref_max: string | null;
  aliases: string[];
  notes: string | null;
};

export type BodyMetric = {
  id: number;
  slug: string;
  name: string;
  unit: string;
  /** Null for a trend-only metric, and while the user's sex is unknown. */
  bands: Band[] | null;
  source: string | null;
  notes: string | null;
};

export type Result = {
  id: string;
  biomarker_id: number;
  biomarker_slug: string;
  biomarker_name: string;
  category: BiomarkerCategory;
  value: string;
  unit: string;
  ref_min: string | null;
  ref_max: string | null;
  flag: ResultFlag | null;
};

export type ReportSummary = {
  id: string;
  collected_on: string;
  lab_name: string;
  fasting: boolean | null;
  source: "manual" | "extracted";
  notes: string | null;
  created_at: string;
  result_count: number;
};

export type Report = Omit<ReportSummary, "result_count"> & { results: Result[] };

export type Intervention = {
  id: string;
  kind: InterventionKind;
  name: string;
  dose: string | null;
  started_on: string;
  ended_on: string | null;
  notes: string | null;
};

export type ScanValue = {
  id: string;
  metric_id: number;
  metric_slug: string;
  metric_name: string;
  unit: string;
  value: string;
  flag: BandFlag | null;
  label: string | null;
};

export type BodyScan = {
  id: string;
  measured_at: string;
  source: "manual" | "import";
  device: string | null;
  notes: string | null;
  values: ScanValue[];
};

export type BodyMetricSummary = {
  metric: BodyMetric;
  latest: ScanValue;
  measured_at: string;
  sparkline: { date: string; value: string }[];
};

export type BiomarkerPoint = {
  date: string;
  value: string;
  unit: string;
  lab_name: string;
  ref_min: string | null;
  ref_max: string | null;
  flag: ResultFlag | null;
  report_id: string;
};

export type BiomarkerSeries = {
  biomarker: Biomarker;
  points: BiomarkerPoint[];
  interventions: Intervention[];
};

export type BodyPoint = {
  date: string;
  value: string;
  flag: BandFlag | null;
  label: string | null;
  scan_id: string;
};

export type BodySeries = {
  metric: BodyMetric;
  points: BodyPoint[];
  interventions: Intervention[];
};

export type DashboardItem = {
  biomarker: Biomarker;
  value: string;
  unit: string;
  flag: ResultFlag | null;
  collected_on: string;
  lab_name: string;
  sparkline: { date: string; value: string }[];
};

export type Dashboard = {
  categories: { category: BiomarkerCategory; items: DashboardItem[] }[];
  last_report_on: string | null;
  report_count: number;
};
