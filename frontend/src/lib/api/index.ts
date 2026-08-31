import { query, request, upload, uploadWithFields } from "./client";
import type {
  Biomarker,
  BiomarkerSeries,
  BodyMetric,
  BodyMetricSummary,
  BodyScan,
  BodySeries,
  CollectionContext,
  Dashboard,
  Doctor,
  ExtractionJob,
  Features,
  Intervention,
  InterventionKind,
  Lab,
  Photo,
  Pose,
  Report,
  ReportSummary,
  Result,
  ResultPrefill,
  Sex,
  Timeline,
  TimelineKind,
  User,
} from "./types";

export type DateWindow = { from?: string; to?: string };

/** Filters the report list accepts. `lab_id` and `doctor_id` come from the
 *  account's own lists, so an id from elsewhere simply matches nothing. */
export type ReportFilter = DateWindow & { lab_id?: string; doctor_id?: string };

export const auth = {
  config: () => request<{ mode: "oidc" | "local" }>("/api/auth/config"),
  me: () => request<User>("/api/users/me"),
  login: (email: string, password: string) =>
    request<User>("/auth/login", { method: "POST", body: { email, password } }),
  register: (payload: { email: string; password: string; name?: string; sex?: Sex | null }) =>
    request<User>("/auth/register", { method: "POST", body: payload }),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  updateProfile: (payload: {
    name?: string | null;
    sex?: Sex | null;
    birth_date?: string | null;
    height_cm?: number | null;
  }) => request<User>("/api/users/me", { method: "PATCH", body: payload }),
};

export const features = {
  read: () => request<Features>("/api/features"),
};

/** One result on the way in. The server derives everything else about it —
 *  the canonical value, the shape of the reference, the flag. */
type ResultPayload = {
  biomarker_id: number;
  value: number;
  unit?: string | null;
  ref_min?: number | null;
  ref_max?: number | null;
  method?: string | null;
  note?: string | null;
};

/** The report itself on the way in. The laboratory and the doctor travel as
 *  names — the server resolves each to the account's own entity, creating it on
 *  first sight, so a form never has to know an id to record a new place. */
type ReportPayload = {
  lab_name: string;
  doctor_name?: string | null;
  notes?: string | null;
  results: ResultPayload[];
} & CollectionContext;

/**
 * The PDF pipeline. `create` only ever produces a preview: nothing an extraction
 * read reaches the history until `confirm` is called with what a human approved.
 */
export const extractions = {
  create: (file: File) => upload<ExtractionJob>("/api/extractions", file),
  read: (id: string) => request<ExtractionJob>(`/api/extractions/${id}`),
  confirm: (id: string, payload: ReportPayload) =>
    request<Report>(`/api/extractions/${id}/confirm`, { method: "POST", body: payload }),
  discard: (id: string) => request<void>(`/api/extractions/${id}`, { method: "DELETE" }),
};

/** Where the history came from — for filtering it, and for pre-filling a new
 *  entry from the last report the same laboratory issued. */
export const providers = {
  labs: () => request<Lab[]>("/api/labs"),
  doctors: () => request<Doctor[]>("/api/doctors"),
};

export const catalogue = {
  biomarkers: () => request<Biomarker[]>("/api/biomarkers"),
  bodyMetrics: () => request<BodyMetric[]>("/api/body/metrics"),
};

export const dashboard = {
  read: () => request<Dashboard>("/api/dashboard"),
};

/** Everything that happened, newest first. Paged by date rather than by offset:
 *  the history grows at the recent end, and an offset would shift every page
 *  under the reader the moment a report is added. */
export const timeline = {
  read: (filter: { kinds?: TimelineKind[]; before?: string } = {}) =>
    request<Timeline>(`/api/timeline${query({ kinds: filter.kinds, before: filter.before })}`),
};

export const biomarkers = {
  series: (id: number) => request<BiomarkerSeries>(`/api/biomarkers/${id}/series`),
};

export const reports = {
  list: (filter: ReportFilter = {}) =>
    request<ReportSummary[]>(
      `/api/reports${query({
        from: filter.from,
        to: filter.to,
        lab_id: filter.lab_id,
        doctor_id: filter.doctor_id,
      })}`,
    ),
  read: (id: string) => request<Report>(`/api/reports/${id}`),
  /** The last reading of every marker, to fill a new entry in. Narrowed to one
   *  laboratory when known, because a reference range belongs to the lab that
   *  issued it and carrying one across is how a history acquires a wrong one. */
  prefill: (labId?: string) =>
    request<ResultPrefill[]>(`/api/reports/prefill${query({ lab_id: labId })}`),
  update: (id: string, payload: { notes?: string | null; doctor_name?: string | null }) =>
    request<Report>(`/api/reports/${id}`, { method: "PATCH", body: payload }),
  annotate: (reportId: string, resultId: string, note: string | null) =>
    request<Result>(`/api/reports/${reportId}/results/${resultId}`, {
      method: "PATCH",
      body: { note },
    }),
  create: (payload: ReportPayload) =>
    request<Report>("/api/reports", { method: "POST", body: payload }),
  remove: (id: string) => request<void>(`/api/reports/${id}`, { method: "DELETE" }),
};

export const interventions = {
  list: (kind?: InterventionKind) =>
    request<Intervention[]>(`/api/interventions${query({ kind })}`),
  create: (payload: {
    kind: InterventionKind;
    name: string;
    dose?: string | null;
    started_on: string;
    ended_on?: string | null;
    notes?: string | null;
  }) => request<Intervention>("/api/interventions", { method: "POST", body: payload }),
  update: (id: string, payload: Partial<{ ended_on: string | null; name: string }>) =>
    request<Intervention>(`/api/interventions/${id}`, { method: "PATCH", body: payload }),
  remove: (id: string) => request<void>(`/api/interventions/${id}`, { method: "DELETE" }),
};

export const photos = {
  list: (filters: DateWindow & { pose?: Pose } = {}) =>
    request<Photo[]>(
      `/api/photos${query({ pose: filters.pose, from: filters.from, to: filters.to })}`,
    ),
  create: (payload: { file: File; taken_on: string; pose: Pose; notes?: string }) =>
    uploadWithFields<Photo>("/api/photos", payload.file, {
      taken_on: payload.taken_on,
      pose: payload.pose,
      ...(payload.notes ? { notes: payload.notes } : {}),
    }),
  remove: (id: string) => request<void>(`/api/photos/${id}`, { method: "DELETE" }),
};

export const body = {
  scans: (window: DateWindow = {}) =>
    request<BodyScan[]>(`/api/body/scans${query({ from: window.from, to: window.to })}`),
  summary: () => request<BodyMetricSummary[]>("/api/body/summary"),
  series: (id: number) => request<BodySeries>(`/api/body/metrics/${id}/series`),
  createScan: (payload: {
    measured_at: string;
    device?: string | null;
    notes?: string | null;
    values: { metric_id: number; value: number }[];
  }) => request<BodyScan>("/api/body/scans", { method: "POST", body: payload }),
  removeScan: (id: string) => request<void>(`/api/body/scans/${id}`, { method: "DELETE" }),
};
