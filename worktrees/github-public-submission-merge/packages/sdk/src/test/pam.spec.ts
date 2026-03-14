import { describe, expect, it } from "vitest";
import {
  canAutoFix,
  generateCorrectionPatch,
  verifyCorrection,
} from "../pam.js";

describe("Pam SDK helpers", () => {
  it("allows soft-project auto-fix when no forbidden violation is present", () => {
    expect(canAutoFix("SOFT_PROJECT", ["FIGMA_TOKEN_REALIGNMENT"])).toBe(true);
  });

  it("rejects auto-fix for hard-reject severities or forbidden violation codes", () => {
    expect(canAutoFix("HARD_REJECT", [])).toBe(false);
    expect(
      canAutoFix("CONTINUOUS_DEVIATION", ["FORBIDDEN_GEOMETRY_MUTATION"]),
    ).toBe(false);
  });

  it("generates replace patches only for mutable figma-backed drift items", () => {
    expect(
      generateCorrectionPatch([
        {
          path: "/style/color",
          currentValue: "#111111",
          idealValue: "#222222",
          figmaBacked: true,
          mutable: true,
        },
        {
          path: "/style/strokeWidth",
          currentValue: 1,
          idealValue: 1,
          figmaBacked: true,
          mutable: true,
        },
        {
          path: "/geometry/spokeCount",
          currentValue: 5,
          idealValue: 6,
          figmaBacked: false,
          mutable: false,
        },
      ]),
    ).toEqual([
      {
        op: "replace",
        path: "/style/color",
        value: "#222222",
      },
    ]);
  });

  it("verifies corrections only when drift is not worsened and violations are cleared", () => {
    expect(
      verifyCorrection({
        ok: true,
        remainingViolations: [],
        driftScoreBefore: 2,
        driftScoreAfter: 0,
      }),
    ).toBe(true);

    expect(
      verifyCorrection({
        ok: true,
        remainingViolations: ["/style/color"],
        driftScoreBefore: 1,
        driftScoreAfter: 1,
      }),
    ).toBe(false);
  });
});
