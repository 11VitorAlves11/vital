import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it } from "vitest";

import {
  SESSION_ROUTES,
  USER,
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
  canonical_unit: "g/dL",
  reference_kind: "two_sided",
  ref_min: "12.0000",
  ref_max: "15.0000",
  reference_bands: null,
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
  trend_reason: null,
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
                  band_label: null,
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
          due_repeats: [],
        },
      },
    ]);
    renderWithProviders(<Dashboard />);
    expect(await screen.findByText("Hematologia")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Hemoglobina" })).toHaveLength(2);
    expect(screen.getAllByText("Baixo")).toHaveLength(2);
  });

  it("lifts what is out of range above the panels", async () => {
    // The reason most sessions are opened. The card is repeated rather than
    // moved, so its panel does not end up with a hole where it used to be.
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
                  band_label: null,
                  collected_on: "2026-03-01",
                  lab_name: "Synlab",
                  sparkline: [],
                },
                {
                  biomarker: { ...HAEMOGLOBIN, id: 2, slug: "plaquetas", name: "Plaquetas" },
                  value: "250.0000",
                  unit: "10^9/L",
                  flag: "normal",
                  band_label: null,
                  collected_on: "2026-03-01",
                  lab_name: "Synlab",
                  sparkline: [],
                },
              ],
            },
          ],
          last_report_on: "2026-03-01",
          report_count: 1,
          due_repeats: [],
        },
      },
    ]);
    renderWithProviders(<Dashboard />);
    expect(await screen.findByRole("heading", { name: "Desde a última colheita" })).toBeInTheDocument();
    // Only the flagged one is lifted; the normal one stays in its panel alone.
    expect(screen.getAllByRole("link", { name: "Hemoglobina" })).toHaveLength(2);
    expect(screen.getAllByRole("link", { name: "Plaquetas" })).toHaveLength(1);
  });

  it("says nothing about range when nothing is out of it", async () => {
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
                  value: "14.0000",
                  unit: "g/dL",
                  flag: "normal",
                  band_label: null,
                  collected_on: "2026-03-01",
                  lab_name: "Synlab",
                  sparkline: [],
                },
              ],
            },
          ],
          last_report_on: "2026-03-01",
          report_count: 1,
          due_repeats: [],
        },
      },
    ]);
    renderWithProviders(<Dashboard />);
    await screen.findByText("Hematologia");
    expect(screen.queryByText("Está agora fora do intervalo de referência.")).not.toBeInTheDocument();
  });

  it("points at the next action when there is nothing recorded", async () => {
    mockApi([
      {
        pattern: /\/api\/dashboard/,
        body: { categories: [], last_report_on: null, report_count: 0, due_repeats: [] },
      },
    ]);
    renderWithProviders(<Dashboard />);
    expect(await screen.findByText("Ainda não há análises")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Registar colheita" })).toBeInTheDocument();
  });

  it("surfaces what is due for repeat, and cancelling removes it", async () => {
    const fetchMock = mockApi([
      {
        pattern: /\/api\/dashboard/,
        body: {
          categories: [],
          last_report_on: "2026-03-01",
          report_count: 1,
          due_repeats: [
            {
              id: "rep-1",
              biomarker_id: 1,
              biomarker_slug: "vitamin-d-25-oh",
              biomarker_name: "Vitamina D (25-OH)",
              target_year: 2026,
              target_month: 3,
              note: "ver suplementação",
              created_at: "2026-01-01T00:00:00Z",
              source_result_id: "res-1",
              status: "due",
            },
          ],
        },
      },
      { pattern: /\/api\/repeats\/rep-1/, body: null },
    ]);
    renderWithProviders(<Dashboard />);

    expect(await screen.findByRole("heading", { name: "1 marcador por repetir" })).toBeInTheDocument();
    const link = screen.getByRole("link", { name: "Vitamina D (25-OH)" });
    expect(link).toHaveAttribute("href", "/biomarkers/1");
    expect(screen.getByText(/Previsto para março de 2026/)).toBeInTheDocument();
    expect(screen.getByText(/ver suplementação/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Cancelar lembrete" }));

    await waitFor(() => {
      const call = fetchMock.mock.calls.find(([, init]) => init?.method === "DELETE");
      expect(call?.[0]).toBe("/api/repeats/rep-1");
    });
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
              canonical_value: "14.0000",
              canonical_ref_min: "12.0000",
              canonical_ref_max: "15.0000",
              ref_min: "12.0000",
              ref_max: "15.0000",
              reference_kind: "two_sided",
              band_label: null,
              method: "Hexoquinase",
              caveats: [{ code: "fasting_unknown", values: {} }],
              flag: "normal",
              report_id: "r1",
            },
          ],
          unit: "g/dL",
          has_unconverted_points: false,
          moments: [
            {
              id: "body_composition:s1",
              kind: "body_composition",
              occurred_on: "2026-01-15",
              occurred_at: null,
              ended_on: null,
              has_duration: false,
              title: "Tanita",
              subtitle: null,
              summary: [],
              href: "/body",
              intervention_kind: null,
              pose: null,
              photo_id: null,
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
    expect(screen.getAllByText("Normal").length).toBeGreaterThan(0);
    expect(screen.getByText(/Ferro/)).toBeInTheDocument();
    // A caveat is shown beside the point it qualifies, not as a page-level alert.
    expect(screen.getByText(/não ficou registado se a colheita foi em jejum/i)).toBeInTheDocument();
    // Events outside the selected data period do not imply a correlation.
    expect(screen.queryByText(/Composição corporal/)).not.toBeInTheDocument();
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
              canonical_value: "14.0000",
              canonical_ref_min: "12.0000",
              canonical_ref_max: "15.0000",
              ref_min: "12.0000",
              ref_max: "15.0000",
              reference_kind: "two_sided",
              band_label: null,
              method: null,
              caveats: [],
              flag: "normal",
              report_id: "r1",
            },
          ],
          unit: "g/dL",
          has_unconverted_points: false,
          moments: [],
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
  it("names the automatic action as importing analyses", async () => {
    mockApi([
      { pattern: /\/api\/features/, body: { extraction: true } },
      { pattern: /\/api\/labs/, body: [] },
      { pattern: /\/api\/reports/, body: [] },
    ]);

    renderWithProviders(<Reports />);

    expect(await screen.findByRole("button", { name: "Importar análises" })).toBeInTheDocument();
  });

  it("lists collections with their result count", async () => {
    mockApi([
      { pattern: /\/api\/features/, body: { extraction: false } },
      {
        pattern: /\/api\/labs/,
        body: [
          { id: "l1", name: "Synlab Braga", report_count: 1, created_at: "2026-03-01T10:00:00Z" },
          { id: "l2", name: "Unilabs", report_count: 2, created_at: "2026-03-01T10:00:00Z" },
        ],
      },
      {
        pattern: /\/api\/reports/,
        body: [
          {
            id: "r1",
            lab_id: "l1",
            doctor_id: null,
            doctor_name: "Dra. Sofia Nunes",
            notes_at: null,
            collected_on: "2026-03-01",
            lab_name: "Synlab Braga",
            collected_at: "2026-01-01T08:15:00",
            fasting_state: "fasting",
            fasting_hours: 12,
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
    expect(screen.getByText(/Dra\. Sofia Nunes/)).toBeInTheDocument();
    // Offered because this account has used more than one laboratory.
    expect(await screen.findByLabelText("Laboratório")).toBeInTheDocument();
  });

  it("opens the manual entry form", async () => {
    mockApi([
      { pattern: /\/api\/features/, body: { extraction: false } },
      { pattern: /\/api\/reports/, body: [] },
      { pattern: /\/api\/labs/, body: [] },
      { pattern: /\/api\/doctors/, body: [] },
      { pattern: /\/api\/biomarkers/, body: [HAEMOGLOBIN] },
    ]);
    renderWithProviders(<Reports />);
    await userEvent.click((await screen.findAllByRole("button", { name: "Registar colheita" }))[0]);
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
  it("shows the standard where one classifies, and the reason where none does", async () => {
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
            metric: {
              ...BMI,
              id: 2,
              slug: "weight",
              name: "Peso",
              bands: null,
              source: null,
              trend_reason: "A leitura clínica faz-se pelo IMC",
            },
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
    expect(screen.getByText("OMS")).toBeInTheDocument();
    // The reason this one carries no verdict, rather than the same four words
    // the page used to repeat on every unclassified metric.
    expect(screen.getByText("A leitura clínica faz-se pelo IMC")).toBeInTheDocument();
    expect(screen.queryByText("Sem referência clínica")).not.toBeInTheDocument();
  });

  it("shows the age-referenced percentile beside the fitness label", async () => {
    mockApi([
      ...SESSION_ROUTES,
      {
        pattern: /\/api\/body\/summary/,
        body: [
          {
            metric: { ...BMI, id: 2, slug: "body-fat-pct", name: "Gordura corporal" },
            latest: {
              id: "v1",
              metric_id: 2,
              metric_slug: "body-fat-pct",
              metric_name: "Gordura corporal",
              unit: "%",
              value: "22.0000",
              flag: null,
              label: "Aceitável",
              age_context: "Abaixo do percentil 10",
            },
            measured_at: "2026-03-01T08:00:00Z",
            sparkline: [{ date: "2026-03-01T08:00:00Z", value: "22.0000" }],
          },
        ],
      },
    ]);
    renderWithSession(<Body />);
    expect(await screen.findByText("Aceitável")).toBeInTheDocument();
    expect(screen.getByText("Abaixo do percentil 10")).toBeInTheDocument();
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
  it("saves account model credentials without showing a stored key", async () => {
    const fetchMock = mockApi([
      {
        pattern: /\/api\/users\/me\/model-settings/,
        body: {
          model: "ollama/llama3.2-vision",
          base_url: "http://localhost:11434",
          has_api_key: true,
          has_account_api_key: true,
          uses_instance_model: false,
          uses_instance_base_url: false,
        },
      },
      ...SESSION_ROUTES,
      { pattern: /\/api\/body\/summary/, body: [] },
    ]);
    renderWithSession(<Profile />);

    expect(await screen.findByLabelText("Modelo")).toHaveValue("ollama/llama3.2-vision");
    expect(screen.getByLabelText("Chave de API")).toHaveAttribute(
      "placeholder",
      "Chave guardada",
    );
    await userEvent.clear(screen.getByLabelText("Modelo"));
    await userEvent.type(screen.getByLabelText("Modelo"), "openai/gpt-4.1-mini");
    await userEvent.type(screen.getByLabelText("Chave de API"), "new-secret-key");
    await userEvent.click(screen.getByRole("button", { name: "Guardar modelo" }));

    await waitFor(() => {
      const patch = fetchMock.mock.calls.find(
        ([url, init]) => String(url).includes("model-settings") && init?.method === "PATCH",
      );
      expect(JSON.parse(String(patch?.[1]?.body))).toMatchObject({
        model: "openai/gpt-4.1-mini",
        api_key: "new-secret-key",
      });
    });
  });

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

  it("carries everything the body-composition references key on", async () => {
    // Sex, age and height: without them BMI, FFMI and every age-specific
    // reference have nothing to be computed against.
    mockApi([
      {
        pattern: /\/api\/users\/me/,
        body: { ...USER, birth_date: "1992-04-15", height_cm: "178.0" },
      },
      ...SESSION_ROUTES,
      { pattern: /\/api\/body\/summary/, body: [] },
    ]);
    renderWithSession(<Profile />);
    await waitFor(() => expect(screen.getByLabelText("Altura")).toHaveValue(178));
    expect(screen.getByLabelText("Data de nascimento")).toHaveValue("1992-04-15");
    // The age is read back from the date rather than asked for separately —
    // storing both would let the two disagree.
    expect(screen.getByText(/34 anos/)).toBeInTheDocument();
  });

  it("shows the latest weight without offering to edit it", async () => {
    mockApi([
      ...SESSION_ROUTES,
      {
        pattern: /\/api\/body\/summary/,
        body: [
          {
            metric: {
              id: 4,
              slug: "weight",
              name: "Peso",
              unit: "kg",
              bands: null,
              source: null,
              notes: null,
            },
            latest: {
              id: "v1",
              metric_id: 4,
              metric_slug: "weight",
              metric_name: "Peso",
              unit: "kg",
              value: "77.2000",
              flag: null,
              label: null,
              derived_from: null,
            },
            measured_at: "2026-05-04T08:00:00Z",
            sparkline: [],
          },
        ],
      },
    ]);
    renderWithSession(<Profile />);
    expect(await screen.findByText(/77,2 kg/)).toBeInTheDocument();
    // Weight is a measurement with a history; two places to change it would
    // mean two answers to what someone weighs.
    expect(screen.queryByLabelText(/peso mais recente/i)).not.toBeInTheDocument();
  });

  it("sends null rather than zero when the height is cleared", async () => {
    const fetchMock = mockApi([
      { pattern: /\/api\/users\/me/, body: { ...USER, height_cm: "178.0" } },
      ...SESSION_ROUTES,
      { pattern: /\/api\/body\/summary/, body: [] },
    ]);
    renderWithSession(<Profile />);
    await waitFor(() => expect(screen.getByLabelText("Altura")).toHaveValue(178));
    await userEvent.clear(screen.getByLabelText("Altura"));
    await userEvent.click(screen.getByRole("button", { name: "Guardar" }));

    await waitFor(() => {
      const patch = fetchMock.mock.calls.find(([, init]) => init?.method === "PATCH");
      expect(JSON.parse(String(patch?.[1]?.body)).height_cm).toBeNull();
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
