import { describe, expect, it } from "vitest";
import { growth, ratio } from "@/lib/metrics";

describe("metric rules", () => {
  it("does not fabricate growth from a missing or negative base", () => {
    expect(growth(100, null)).toBeNull();
    expect(growth(100, -20)).toBeNull();
    expect(growth(150, 100)).toBeCloseTo(0.5);
  });
  it("returns null for ratios with a zero denominator", () => {
    expect(ratio(5, 0)).toBeNull();
  });
});
