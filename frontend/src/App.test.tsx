import { render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";

import { App } from "./App";

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() =>
      Promise.resolve({ ok: true, json: () => Promise.resolve({ name: "Vital", version: "0.1.0" }) }),
    ),
  );
});

it("renders the app name", async () => {
  render(<App />);
  expect(await screen.findByRole("heading", { name: "Vital" })).toBeInTheDocument();
  await screen.findByText(/API Vital/);
});

it("shows the API version once it loads", async () => {
  render(<App />);
  expect(await screen.findByText("API Vital v0.1.0")).toBeInTheDocument();
});
