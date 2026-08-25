import { query, request } from "./client";
import type {
  Biomarker,
  BiomarkerSeries,
  BodyMetric,
  BodyMetricSummary,
  BodyScan,
  BodySeries,
  Dashboard,
  Intervention,
  InterventionKind,
  Report,
  ReportSummary,
  Sex,
  User,
} from "./types";

export type DateWindow = { from?: string; to?: string };

export const auth = {
  config: () => request<{ mode: "oidc" | "local" }>("/api/auth/config"),
  me: () => request<User>("/api/users/me"),
  login: (email: string, password: string) =>
    request<User>("/auth/login", { method: "POST", body: { email, password } }),
  register: (payload: { email: string; password: string; name?: string; sex?: Sex | null }) =>
    request<User>("/auth/register", { method: "POST", body: payload }),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  updateProfile: (payload: { name?: string | null; sex?: Sex | null }) =>
    request<User>("/api/users/me", { method: "PATCH", body: payload }),
};

export const catalogue = {
  biomarkers: () => request<Biomarker[]>("/api/biomarkers"),
  bodyMetrics: () => request<BodyMetric[]>("/api/body/metrics"),
};

export const dashboard = {
  read: () => request<Dashboard>("/api/dashboard"),
};

export const biomarkers = {
  series: (id: number) => request<BiomarkerSeries>(`/api/biomarkers/${id}/series`),
};

export const reports = {
  list: (window: DateWindow = {}) =>
    request<ReportSummary[]>(`/api/reports${query({ from: window.from, to: window.to })}`),
  read: (id: string) => request<Report>(`/api/reports/${id}`),
  create: (payload: {
    collected_on: string;
    lab_name: string;
    fasting?: boolean | null;
    notes?: string | null;
    results: {
      biomarker_id: number;
      value: number;
      unit?: string | null;
      ref_min?: number | null;
      ref_max?: number | null;
    }[];
  }) => request<Report>("/api/reports", { method: "POST", body: payload }),
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
