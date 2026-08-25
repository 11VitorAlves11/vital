import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it } from "vitest";

import {
  SESSION_ROUTES,
  mockApi,
  renderWithProviders,
  renderWithSession,
  setViewport,
  usePortuguese,
} from "../test/utils";
import { BiomarkerDetail } from "./BiomarkerDetail";
import { Body } from "./Body";
import { Dashboard } from "./Dashboard";
import { Interventions } from "./Interventions";
import { Login } from "./Login";
import { Profile } from "./Profile";
import { Reports } from "./Reports";

const HAEMOGLOBIN = {
  id: 1,
  slug: "hemoglobina",
  name: "Hemoglobina",
  category: "hematologia",
  unit_default: "g/dL",
  ref_min: "12.0000",
  ref_max: "15.0000",
  aliases: ["Hb"],
  notes: null,
};

const BMI = {
  id: 1,
  slug: "bmi",
  name: "IMC",
  unit: "kg/m²",
  bands: [{ label: "Pré-obesidade", min: 25, max: 30, flag: "warn" }],
  source: "OMS",
  notes: null,
};

beforeAll(async () => {
  await usePortuguese();
  setViewport("mobile");
});

describe("Login", () => {
  it("offers the local form when the server says AUTH_MODE=local", async () => {
    mockApi([
      { pattern: /\/api\/auth\/config/, body: { mode: "local" } },
      { pattern: /\/api\/users\/me/, body: {}, status: 401 },
    ]);
    renderWithSession(<Login />);
    expect(await screen.findByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByLabelText("Palavra-passe")).toBeInTheDocument();
  });

  it("offers the provider redirect when the server says AUTH_MODE=oidc", async () => {
    mockApi([
      { pattern: /\/api\/auth\/config/, body: { mode: "oidc" } },
      { pattern: /\/api\/users\/me/, body: {}, status: 401 },
    ]);
    renderWithSession(<Login />);
    expect(
      await screen.findByRole("button", { name: "Entrar com o fornecedor de identidade" }),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText("Palavra-passe")).not.toBeInTheDocument();
  });

  it("reports invalid credentials next to the form", async () => {
    mockApi([
      { pattern: /\/api\/auth\/config/, body: { mode: "local" } },
      { pattern: /\/api\/users\/me/, body: {}, status: 401 },
      { pattern: /\/auth\/login/, body: { detail: "Invalid email or password" }, status: 401 },
    ]);
    renderWithSession(<Login />);
    await userEvent.type(await screen.findByLabelText("Email"), "ana@example.com");
    await userEvent.type(screen.getByLabelText("Palavra-passe"), "errada");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Email ou palavra-passe inválidos.");
  });
});

describe("Dashboard", () => {
  it("groups cards by panel and shows the flag with its label", async () => {
    mockApi([
      {
        pattern: /\/api\/dashboard/,
        body: {
          categories: [
            {
              category: "hematologia",
              items: [
                {
                  biomarker: HAEMOGLOBIN,
                  value: "11.0000",
                  unit: "g/dL",
                  flag: "low",
                  collected_on: "2026-03-01",
                  lab_name: "Synlab",
                  sparkline: [
                    { date: "2026-01-01", value: "12.0000" },
                    { date: "2026-03-01", value: "11.0000" },
                  ],
                },
              ],
            },
          ],
          last_report_on: "2026-03-01",
          report_count: 2,
        },
      },
    ]);
    renderWithProviders(<Dashboard />);
    expect(await screen.findByRole("heading", { name: "Hematologia" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Hemoglobina" })).toBeInTheDocument();
    expect(screen.getByText("11")).toBeInTheDocument();
    expect(screen.getByText("Baixo")).toBeInTheDocument();
  });

  it("points at the next action when there is nothing recorded", async () => {
    mockApi([
      {
        pattern: /\/api\/dashboard/,
        body: { categories: [], last_report_on: null, report_count: 0 },
      },
    ]);
    renderWithProviders(<Dashboard />);
    expect(await screen.findByText("Ainda não há análises")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Registar colheita" })).toBeInTheDocument();
  });

  it("keeps the failure beside the content, with a retry", async () => {
    mockApi([{ pattern: /\/api\/dashboard/, body: { detail: "boom" }, status: 500 }]);
    renderWithProviders(<Dashboard />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Tentar novamente" })).toBeInTheDocument();
  });
});

describe("BiomarkerDetail", () => {
  it("renders the chart, the overlay and the history table", async () => {
    mockApi([
      {
        pattern: /\/api\/biomarkers\/1\/series/,
        body: {
          biomarker: HAEMOGLOBIN,
          points: [
            {
              date: "2026-01-01",
              value: "14.0000",
              unit: "g/dL",
              lab_name: "Synlab",
              ref_min: "12.0000",
              ref_max: "15.0000",
              flag: "normal",
              report_id: "r1",
            },
          ],
          interventions: [
            {
              id: "i1",
              kind: "suplemento",
              name: "Ferro",
              dose: "25 mg",
              started_on: "2025-12-01",
              ended_on: null,
              notes: null,
            },
          ],
        },
      },
    ]);
    renderWithProviders(<BiomarkerDetail />, {
      route: "/biomarkers/1",
      path: "/biomarkers/:id",
    });
    expect(await screen.findByRole("heading", { name: "Hemoglobina" })).toBeInTheDocument();
    expect(screen.getByRole("img")).toHaveAccessibleName(/Hemoglobina/);
    // The history is the chart's textual alternative, so it is not optional.
    expect(screen.getByText(/Synlab/)).toBeInTheDocument();
    expect(screen.getByText("Normal")).toBeInTheDocument();
    expect(screen.getByText(/Ferro/)).toBeInTheDocument();
  });

  it("shows the history as a dense table on a desktop", async () => {
    setViewport("desktop");
    mockApi([
      {
        pattern: /\/api\/biomarkers\/1\/series/,
        body: {
          biomarker: HAEMOGLOBIN,
          points: [
            {
              date: "2026-01-01",
              value: "14.0000",
              unit: "g/dL",
              lab_name: "Synlab",
              ref_min: "12.0000",
              ref_max: "15.0000",
              flag: "normal",
              report_id: "r1",
            },
          ],
          interventions: [],
        },
      },
    ]);
    renderWithProviders(<BiomarkerDetail />, {
      route: "/biomarkers/1",
      path: "/biomarkers/:id",
    });
    expect(await screen.findByRole("table")).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Laboratório" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Synlab" })).toBeInTheDocument();
  });
});

describe("Reports", () => {
  it("lists collections with their result count", async () => {
    mockApi([
      { pattern: /\/api\/features/, body: { extraction: false } },
      {
        pattern: /\/api\/reports/,
        body: [
          {
            id: "r1",
            collected_on: "2026-03-01",
            lab_name: "Synlab Braga",
            fasting: true,
            source: "manual",
            notes: null,
            created_at: "2026-03-01T10:00:00Z",
            result_count: 3,
            has_file: false,
          },
        ],
      },
    ]);
    renderWithProviders(<Reports />);
    expect(await screen.findByText("Synlab Braga")).toBeInTheDocument();
    expect(screen.getByText("3 resultados")).toBeInTheDocument();
  });

  it("opens the manual entry form", async () => {
    mockApi([
      { pattern: /\/api\/features/, body: { extraction: false } },
      { pattern: /\/api\/reports/, body: [] },
      { pattern: /\/api\/biomarkers/, body: [HAEMOGLOBIN] },
    ]);
    renderWithProviders(<Reports />);
    await userEvent.click(
      (await screen.findAllByRole("button", { name: "Registar colheita" }))[0],
    );
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    expect(screen.getByLabelText("Data da colheita")).toBeInTheDocument();
    expect(screen.getByLabelText("Biomarcador")).toBeInTheDocument();
  });
});

describe("Interventions", () => {
  it("shows an open intervention as ongoing and offers to end it", async () => {
    mockApi([
      {
        pattern: /\/api\/interventions/,
        body: [
          {
            id: "i1",
            kind: "suplemento",
            name: "Creatina",
            dose: "5 g/dia",
            started_on: "2026-01-01",
            ended_on: null,
            notes: null,
          },
        ],
      },
    ]);
    renderWithProviders(<Interventions />);
    expect(await screen.findByText("Creatina")).toBeInTheDocument();
    expect(screen.getByText(/Em curso/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Terminar" })).toBeInTheDocument();
  });
});

describe("Body", () => {
  it("shows the clinical band label and marks trend-only metrics as unreferenced", async () => {
    mockApi([
      ...SESSION_ROUTES,
      {
        pattern: /\/api\/body\/summary/,
        body: [
          {
            metric: BMI,
            latest: {
              id: "v1",
              metric_id: 1,
              metric_slug: "bmi",
              metric_name: "IMC",
              unit: "kg/m²",
              value: "27.0000",
              flag: "warn",
              label: "Pré-obesidade",
            },
            measured_at: "2026-03-01T08:00:00Z",
            sparkline: [{ date: "2026-03-01T08:00:00Z", value: "27.0000" }],
          },
          {
            metric: { ...BMI, id: 2, slug: "weight", name: "Peso", bands: null, source: null },
            latest: {
              id: "v2",
              metric_id: 2,
              metric_slug: "weight",
              metric_name: "Peso",
              unit: "kg",
              value: "82.0000",
              flag: null,
              label: null,
            },
            measured_at: "2026-03-01T08:00:00Z",
            sparkline: [{ date: "2026-03-01T08:00:00Z", value: "82.0000" }],
          },
        ],
      },
    ]);
    renderWithSession(<Body />);
    expect(await screen.findByText("Pré-obesidade")).toBeInTheDocument();
    expect(screen.getByText("Sem referência clínica")).toBeInTheDocument();
  });

  it("asks for the missing sex instead of showing values it cannot classify", async () => {
    mockApi([
      { pattern: /\/api\/auth\/config/, body: { mode: "local" } },
      {
        pattern: /\/api\/users\/me/,
        body: {
          id: "u1",
          email: "sem@example.com",
          name: null,
          sex: null,
          birth_date: null,
          created_at: "2026-01-01T00:00:00Z",
        },
      },
      { pattern: /\/api\/body\/summary/, body: [] },
    ]);
    renderWithSession(<Body />);
    expect(await screen.findByText("Indica o sexo no perfil")).toBeInTheDocument();
  });
});

describe("Profile", () => {
  it("saves the sex, which is what every band and range depends on", async () => {
    const fetchMock = mockApi([
      ...SESSION_ROUTES,
      { pattern: /\/api\/users\/me/, body: { ...SESSION_ROUTES[1].body } },
    ]);
    renderWithSession(<Profile />);
    await waitFor(() => expect(screen.getByLabelText("Sexo")).toHaveValue("F"));

    await userEvent.selectOptions(screen.getByLabelText("Sexo"), "M");
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => {
      const patch = fetchMock.mock.calls.find(([, init]) => init?.method === "PATCH");
      expect(patch?.[1]?.body).toContain('"sex":"M"');
    });
  });

  it("switches the interface language", async () => {
    mockApi(SESSION_ROUTES);
    renderWithSession(<Profile />);
    await userEvent.selectOptions(await screen.findByLabelText("Idioma"), "en");
    expect(await screen.findByLabelText("Language")).toBeInTheDocument();
    await usePortuguese();
  });
});
