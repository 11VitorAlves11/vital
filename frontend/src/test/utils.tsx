import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { I18nextProvider } from "react-i18next";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import { ToastProvider } from "../components/ui/Toast";
import i18n from "../lib/i18n";
import { SessionProvider } from "../lib/session";

/** Tests assert against the PT-PT strings, the locale the app is written in. */
export async function usePortuguese() {
  await i18n.changeLanguage("pt-PT");
}

type Viewport = "mobile" | "desktop";

/** Drives `useMediaQuery`, which jsdom cannot answer on its own. */
export function setViewport(viewport: Viewport) {
  const matches = viewport === "desktop";
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    configurable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
}

type Route = { pattern: RegExp; body: unknown; status?: number };

/**
 * Answers fetch from a routing table instead of the network. Anything the test
 * did not declare fails loudly rather than resolving to an empty object.
 */
export function mockApi(routes: Route[]) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    void init;
    const url = typeof input === "string" ? input : input.toString();
    const route = routes.find((candidate) => candidate.pattern.test(url));
    if (!route) throw new Error(`Unmocked request: ${url}`);
    const status = route.status ?? 200;
    return {
      ok: status < 400,
      status,
      statusText: "",
      json: async () => route.body,
    } as Response;
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

type RenderOptions = {
  route?: string;
  /** Route pattern, when the page reads params out of the URL. */
  path?: string;
};

function wrap(ui: ReactElement, path: string | undefined) {
  return path ? <Routes>{<Route path={path} element={ui} />}</Routes> : ui;
}

export function renderWithProviders(ui: ReactElement, { route = "/", path }: RenderOptions = {}) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <I18nextProvider i18n={i18n}>
        <ToastProvider>{wrap(ui, path)}</ToastProvider>
      </I18nextProvider>
    </MemoryRouter>,
  );
}

/** Same, plus a signed-in session — the state every page but Login assumes. */
export function renderWithSession(ui: ReactElement, { route = "/", path }: RenderOptions = {}) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <I18nextProvider i18n={i18n}>
        <SessionProvider>
          <ToastProvider>{wrap(ui, path)}</ToastProvider>
        </SessionProvider>
      </I18nextProvider>
    </MemoryRouter>,
  );
}

export const USER = {
  id: "11111111-1111-1111-1111-111111111111",
  email: "ana@example.com",
  name: "Ana",
  sex: "F" as const,
  birth_date: null,
  height_cm: null,
  created_at: "2026-01-01T00:00:00Z",
};

/** The two calls SessionProvider makes on mount, for tests that do not care. */
export const SESSION_ROUTES = [
  { pattern: /\/api\/auth\/config/, body: { mode: "local" } },
  { pattern: /\/api\/users\/me$/, body: USER },
];
