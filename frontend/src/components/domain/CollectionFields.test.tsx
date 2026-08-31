import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeAll, describe, expect, it, vi } from "vitest";

import { formatTime } from "../../lib/format";
import { renderWithProviders, usePortuguese } from "../../test/utils";
import type { CollectionDraft } from "./CollectionFields";
import { CollectionFields, emptyCollection, toCollectionContext } from "./CollectionFields";

const FASTED: CollectionDraft = {
  collectedOn: "2026-03-01",
  collectedTime: "08:15",
  fastingState: "fasting",
  fastingHours: "12",
};

beforeAll(async () => {
  await usePortuguese();
});

describe("toCollectionContext", () => {
  it("sends the hour as a local moment on the collection date", () => {
    // No offset, and the same day: the API refuses either mistake, and both
    // would silently move a draw to another hour or another day.
    expect(toCollectionContext(FASTED).collected_at).toBe("2026-03-01T08:15:00");
  });

  it("leaves the hour out when nobody recorded one", () => {
    const context = toCollectionContext(emptyCollection("2026-03-01"));
    expect(context.collected_at).toBeNull();
    // Not "they had eaten" — nobody said.
    expect(context.fasting_state).toBe("unknown");
  });

  it("drops the hours of a fast that is no longer claimed", () => {
    const context = toCollectionContext({ ...FASTED, fastingState: "not_fasting" });
    expect(context.fasting_hours).toBeNull();
  });

  it("treats a half-typed number as no answer rather than as zero", () => {
    expect(toCollectionContext({ ...FASTED, fastingHours: "" }).fasting_hours).toBeNull();
  });
});

describe("CollectionFields", () => {
  it("offers fasting as three answers, not a checkbox", () => {
    renderWithProviders(
      <CollectionFields value={emptyCollection("2026-03-01")} onChange={vi.fn()} />,
    );
    const select = screen.getByLabelText("Jejum");
    expect(select).toHaveValue("unknown");
    expect(screen.getByRole("option", { name: "Não registado" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Sem jejum" })).toBeInTheDocument();
  });

  it("asks for the hours only once a fast is claimed", async () => {
    const onChange = vi.fn();
    const { rerender } = renderWithProviders(
      <CollectionFields value={emptyCollection("2026-03-01")} onChange={onChange} />,
    );
    expect(screen.queryByLabelText(/horas de jejum/i)).not.toBeInTheDocument();

    await userEvent.selectOptions(screen.getByLabelText("Jejum"), "fasting");
    expect(onChange).toHaveBeenCalledWith({ fastingState: "fasting" });

    rerender(<CollectionFields value={FASTED} onChange={onChange} />);
    expect(screen.getByLabelText(/horas de jejum/i)).toHaveValue(12);
  });
});

describe("formatTime", () => {
  it("reads the hour off the string instead of through the reader's timezone", () => {
    // Parsed as a Date, an 08:15 draw would land at another hour for anyone not
    // in the zone it was drawn in — including, near midnight, on another day.
    expect(formatTime("2026-03-01T08:15:00", "pt-PT")).toBe("08:15");
  });
});
