import "@testing-library/jest-dom/vitest";
import { afterEach, beforeEach, vi } from "vitest";

import { setViewport } from "./utils";

// Nor does jsdom have ResizeObserver, which Recharts' ResponsiveContainer requires.
if (!globalThis.ResizeObserver) {
  globalThis.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
}

beforeEach(() => {
  // jsdom has no matchMedia, and every responsive decision goes through it.
  // Re-applied per test because restoring mocks strips the implementation.
  setViewport("mobile");
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});
