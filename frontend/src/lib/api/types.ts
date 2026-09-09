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

/** A laboratory or a doctor this account has actually used. Per-account, not
 *  global: a shared instance must not leak where other people go. */
export type Lab = {
  id: string;
  name: string;
  report_count: number;
  created_at: string;
};

export type Doctor = Lab & { specialty: string | null };

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
  /** Decimal string, in centimetres. What turns a weight into a BMI and a
   *  fat-free mass into an FFMI — where the references actually live. */
  height_cm: string | null;
  created_at: string;
};

export type Band = {
  label: string;
  min: number | null;
  max: number | null;
  /** Null on a scale that names without judging — the ACE body-fat categories
   *  are fitness classes, so the label travels and the verdict does not. */
  flag: BandFlag | null;
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
  /** The standard behind the bands, for a metric that classifies. */
  source: string | null;
  /** Why this metric carries no verdict, in one line. Set on every metric that
   *  cannot flag — the card shows it where a classified metric shows `source`. */
  trend_reason: string | null;
  notes: string | null;
};

export type Result = {
  /** Null for a value the server computed rather than stored — nothing to
   *  annotate or schedule a repeat from. */
  id: string | null;
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
  /** Percentage from the lower to the upper bound of a finite interval. */
  range_position?: string | null;
  /** The assay behind the number, as the report named it. */
  method: string | null;
  /** Context someone wrote against this one value, and when. */
  note: string | null;
  note_at: string | null;
  caveats: Caveat[];
  flag: ResultFlag | null;
  /** The measured markers this value was computed from, by name, in formula
   *  order. Null for anything the laboratory actually printed. */
  derived_from: string[] | null;
};

/** What the last reading of a marker looked like — a suggestion the form fills
 *  in and the reader can overwrite. Nothing here is applied server-side. */
export type ResultPrefill = {
  biomarker_id: number;
  unit: string;
  ref_min: string | null;
  ref_max: string | null;
  method: string | null;
  /** Where and when it comes from, so it can be shown and doubted. */
  lab_name: string;
  collected_on: string;
  /** Whether it came from the laboratory this report is for. A range from
   *  another laboratory is that laboratory's and must not be carried across. */
  same_lab: boolean;
};

export type ReportSummary = CollectionContext & {
  id: string;
  lab_id: string;
  lab_name: string;
  doctor_id: string | null;
  doctor_name: string | null;
  source: "manual" | "extracted";
  notes: string | null;
  /** When the note was last written, so an old reading is not read as current. */
  notes_at: string | null;
  created_at: string;
  result_count: number;
  /** Whether the original document is still on the server for this report. */
  has_file: boolean;
};

export type Report = Omit<ReportSummary, "result_count"> & { results: Result[] };

/** One biomarker across two collections. Either side is null when only one of
 *  them measured it — a marker that was dropped or added is part of the diff. */
export type ComparisonRow = {
  biomarker_id: number;
  biomarker_slug: string;
  biomarker_name: string;
  category: BiomarkerCategory;
  previous: Result | null;
  current: Result | null;
  /** Later minus earlier, in `unit`. Null when the two had no common scale. */
  delta: string | null;
  /** Against the earlier value, in per cent. Null when that value was zero. */
  percent_change: string | null;
  /** The unit the difference is in, which is not always either report's own. */
  unit: string | null;
  /** Why the two numbers may not be strictly subtractable. */
  caveats: Caveat[];
};

/** Two collections side by side, oldest first whatever order they were asked in. */
export type ReportComparison = {
  previous: ReportSummary;
  current: ReportSummary;
  rows: ComparisonRow[];
};

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
  /** Null for a derived index, which is computed on read and never stored. */
  id: string | null;
  metric_id: number;
  metric_slug: string;
  metric_name: string;
  unit: string;
  value: string;
  flag: BandFlag | null;
  label: string | null;
  /** The metric this was computed from, for the indices height makes possible.
   *  Null on a measured value — the distinction is the reader's to see. */
  derived_from: string | null;
  /** Which age-referenced percentile bracket this reading falls in, at the
   *  age its owner was on the date of the scan. Null outside every bracket
   *  the reference covers, and for every metric that has none at all. */
  age_context: string | null;
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
  /** Point events inside the same period, drawn as vertical marks. Lab reports
   *  are absent on purpose: on this chart they are the points themselves. */
  moments: TimelineEvent[];
};

export type BodyPoint = {
  date: string;
  value: string;
  flag: BandFlag | null;
  label: string | null;
  /** The age-referenced percentile bracket this point fell in, at the age its
   *  owner was on this date. */
  age_context: string | null;
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

/** What a row on the timeline is, and therefore its icon and its colour.
 *  `intervention` covers everything the intervention model records — supplements,
 *  medication, diets, training blocks — with the specific kind alongside it. */
export type TimelineKind =
  "lab_report" | "body_composition" | "progress_photo" | "appointment" | "imaging" | "intervention";

export type TimelineSummaryItem = {
  label: string;
  value: string;
  flag: ResultFlag | null;
};

/** Already worded for display: the server is the only place that can phrase a
 *  summary once for every client. */
export type TimelineEvent = {
  id: string;
  kind: TimelineKind;
  occurred_on: string;
  /** The hour, only where it means something. */
  occurred_at: string | null;
  ended_on: string | null;
  /** A period rather than a moment — drawn as a bar, not a node. */
  has_duration: boolean;
  title: string;
  subtitle: string | null;
  summary: TimelineSummaryItem[];
  href: string | null;
  intervention_kind: InterventionKind | null;
  pose: Pose | null;
  photo_id: string | null;
};

export type Timeline = {
  events: TimelineEvent[];
  /** Only the kinds this account has anything of; the filter offers no others. */
  available_kinds: TimelineKind[];
  /** The cursor for the next page, or null at the end of the history. */
  next_before: string | null;
};

export type Dashboard = {
  categories: { category: BiomarkerCategory; items: DashboardItem[] }[];
  last_report_on: string | null;
  report_count: number;
  /** Schedules whose target month has arrived with nothing newer recorded
   *  since. Upcoming and fulfilled ones live only on GET /api/repeats. */
  due_repeats: ScheduledRepeat[];
};

/** Whether a schedule still needs acting on — derived server-side on every
 *  read, never stored: a newer result for the marker fulfils it on its own. */
export type RepeatStatus = "upcoming" | "due" | "fulfilled";

/** A reminder to repeat one biomarker around a future month, created from a
 *  result. `source_result_id` goes null if that report is later deleted — the
 *  schedule itself survives, checked against the date it snapshotted. */
export type ScheduledRepeat = {
  id: string;
  biomarker_id: number;
  biomarker_slug: string;
  biomarker_name: string;
  target_year: number;
  target_month: number;
  note: string | null;
  created_at: string;
  source_result_id: string | null;
  status: RepeatStatus;
};
