/** Mirrors the response models in backend/app/schemas. */

export type Sex = "M" | "F";
export type ResultFlag = "low" | "normal" | "high";
export type BandFlag = "normal" | "warn" | "alert";

/** The shape of the interval a value is read against. `none` means no interval
 *  applies — the value is charted, never classified. */
export type ReferenceKind = "two_sided" | "upper_bound" | "lower_bound" | "ordinal_bands" | "none";

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

/** Whether the draw was fasted. `unknown` is "nobody recorded it", which is a
 *  different fact from "they had eaten" and the only one worth prompting about. */
export type FastingState = "fasting" | "not_fasting" | "unknown";

/** The order the form offers them in, and the only values the API accepts. */
export const FASTING_STATES: FastingState[] = ["unknown", "fasting", "not_fasting"];

/** A reason to read a value with care. The server sends the code and the values
 *  that go in the sentence; the sentence itself is a translation. */
export type Caveat = {
  code: string;
  values: Record<string, string>;
};

/** The pre-analytical context of a draw, as the API takes and returns it. */
export type CollectionContext = {
  collected_on: string;
  /** Local wall-clock moment, no offset. Its date has to be `collected_on`. */
  collected_at: string | null;
  fasting_state: FastingState;
  fasting_hours: number | null;
};

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

/** One step of an ordinal scale, in the biomarker's canonical unit. */
export type ReferenceBand = {
  label: string;
  min: number | null;
  max: number | null;
  flag: ResultFlag;
};

export type Biomarker = {
  id: number;
  slug: string;
  name: string;
  category: BiomarkerCategory;
  unit_default: string;
  /** The unit every series of this marker is charted in. */
  canonical_unit: string;
  /** The shape that applies to the caller — `none` when their sex is unknown
   *  and the catalogue only offers sex-specific ranges. */
  reference_kind: ReferenceKind;
  /** Canonical range for the caller's sex; null when their sex is unknown. */
  ref_min: string | null;
  ref_max: string | null;
  /** Set only for `ordinal_bands` markers, where the scale replaces the range. */
  reference_bands: ReferenceBand[] | null;
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
  /** As the laboratory reported it — the number the report itself shows. */
  value: string;
  unit: string;
  /** The same reading in the catalogue's unit; null when it was not convertible. */
  canonical_value: string | null;
  canonical_unit: string | null;
  ref_min: string | null;
  ref_max: string | null;
  reference_kind: ReferenceKind;
  reference_bands: ReferenceBand[] | null;
  /** Which step of an ordinal scale it landed on ("insuficiência"). */
  band_label: string | null;
  /** The assay behind the number, as the report named it. */
  method: string | null;
  caveats: Caveat[];
  flag: ResultFlag | null;
};

export type ReportSummary = CollectionContext & {
  id: string;
  lab_name: string;
  source: "manual" | "extracted";
  notes: string | null;
  created_at: string;
  result_count: number;
  /** Whether the original PDF is still on the server for this report. */
  has_file: boolean;
};

export type Report = Omit<ReportSummary, "result_count"> & { results: Result[] };

export type ExtractionStatus = "pending" | "processing" | "preview" | "confirmed" | "failed";

/** One line as the model read it, paired with the catalogue entry it matched.
 *  `biomarker_id` is null when nothing matched — the row is shown anyway, for
 *  the reader to match by hand or drop. */
export type PreviewResult = {
  biomarker_id: number | null;
  biomarker_name: string | null;
  biomarker_slug: string | null;
  source_name: string;
  value: string | null;
  unit: string | null;
  ref_min: string | null;
  ref_max: string | null;
  method: string | null;
};

export type ExtractionPreview = {
  collected_on: string | null;
  collected_at: string | null;
  lab_name: string | null;
  fasting_state: FastingState;
  results: PreviewResult[];
};

export type ExtractionJob = {
  id: string;
  status: ExtractionStatus;
  filename: string | null;
  provider: string | null;
  error: string | null;
  report_id: string | null;
  created_at: string;
  preview: ExtractionPreview | null;
};

export type Features = { extraction: boolean };

export type Pose = "frente" | "lado" | "costas" | "outro";

/** The order the filter offers them in, and the only values the API accepts. */
export const POSES: Pose[] = ["frente", "lado", "costas", "outro"];

export type Photo = {
  id: string;
  taken_on: string;
  pose: Pose;
  /** Of the stored image, so a gallery can reserve its box before it loads. */
  width: number;
  height: number;
  notes: string | null;
  created_at: string;
};

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
  /** As reported, in `unit` — what the table and the tooltip show. */
  value: string;
  unit: string;
  /** In the series' own unit — what the line is plotted from. */
  canonical_value: string | null;
  lab_name: string;
  ref_min: string | null;
  ref_max: string | null;
  /** The lab's limits on the series' scale, so band and line share an axis. */
  canonical_ref_min: string | null;
  canonical_ref_max: string | null;
  reference_kind: ReferenceKind;
  band_label: string | null;
  method: string | null;
  /** Why this point may not be strictly comparable to the one before it. */
  caveats: Caveat[];
  flag: ResultFlag | null;
  report_id: string;
};

export type BiomarkerSeries = {
  biomarker: Biomarker;
  points: BiomarkerPoint[];
  /** The unit the whole series is plotted in, whatever the reports used. */
  unit: string;
  /** True when a point could not be converted into it, so the line has a gap. */
  has_unconverted_points: boolean;
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
  band_label: string | null;
  collected_on: string;
  lab_name: string;
  sparkline: { date: string; value: string }[];
};

export type Dashboard = {
  categories: { category: BiomarkerCategory; items: DashboardItem[] }[];
  last_report_on: string | null;
  report_count: number;
};
