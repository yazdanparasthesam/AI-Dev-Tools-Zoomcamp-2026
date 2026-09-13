import { describe, expect, it } from "vitest";

import {
  cancelReasonLabel,
  formatClock,
  formatEstimate,
  formatWaitSoFar,
  guestLabel,
  tableLabel,
} from "./format";

const NOW = new Date("2026-09-12T18:30:00Z");

describe("formatEstimate", () => {
  it("reads as seating now for the first party", () => {
    expect(formatEstimate(0)).toBe("Seating now");
  });

  it("shows the estimate from rule R2", () => {
    expect(formatEstimate(10)).toBe("~10 min wait");
    expect(formatEstimate(20)).toBe("~20 min wait");
  });

  it("handles a missing estimate", () => {
    expect(formatEstimate(null)).toBe("—");
  });
});

describe("formatWaitSoFar", () => {
  it("counts whole minutes since arrival", () => {
    expect(formatWaitSoFar("2026-09-12T18:09:00Z", NOW)).toBe("waiting 21 min");
  });

  it("reads as just now under a minute", () => {
    expect(formatWaitSoFar("2026-09-12T18:29:30Z", NOW)).toBe("just now");
  });

  it("singularises one minute", () => {
    expect(formatWaitSoFar("2026-09-12T18:29:00Z", NOW)).toBe("waiting 1 min");
  });

  it("never goes negative if the clock is ahead of the server", () => {
    expect(formatWaitSoFar("2026-09-12T19:00:00Z", NOW)).toBe("just now");
  });
});

describe("labels", () => {
  it("pluralises guests and seats", () => {
    expect(guestLabel(1)).toBe("1 guest");
    expect(guestLabel(4)).toBe("4 guests");
    expect(tableLabel(1)).toBe("1 seat");
    expect(tableLabel(6)).toBe("6 seats");
  });

  it("maps cancel reason codes to human labels", () => {
    expect(cancelReasonLabel("no_show")).toBe("No show");
    expect(cancelReasonLabel("walked")).toBe("Walked out");
    expect(cancelReasonLabel(null)).toBe("Cancelled");
  });

  it("formats a clock time and tolerates null", () => {
    expect(formatClock(null)).toBe("—");
    expect(formatClock("not-a-date")).toBe("—");
    expect(formatClock("2026-09-12T18:05:00Z")).not.toBe("—");
  });
});
