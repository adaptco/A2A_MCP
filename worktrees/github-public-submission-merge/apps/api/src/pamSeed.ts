import { canAutoFix, type PamAutoFixCandidate, type PamRuntimeLane } from "@world-os/sdk";

export function buildPamSeedCandidate(): PamAutoFixCandidate {
  const tokenRefs = {
    "style.strokeWidth": "border/subtle/default",
    "style.color": "theme/racing_sand_metallic",
  };

  return {
    requestType: "BLUEPRINT_RE_SKETCH",
    nodeId: "0x1984_Q9",
    violationId: "viol_00142",
    severity: "SOFT_PROJECT",
    violationCodes: ["SOFT_PROJECT", "FIGMA_TOKEN_REALIGNMENT"],
    componentId: "governance.threshold.panel",
    telemetrySnapshotId: "snap_2026_03_10T14_00_00Z",
    figmaSyncVersion: "v128",
    currentState: {
      style: {
        strokeWidth: 1.2,
        color: "#C79A39",
      },
    },
    idealState: {
      style: {
        strokeWidth: 1.0,
        color: "#C89B3C",
      },
    },
    tokenRefs,
    driftInputs: [
      {
        path: "/style/strokeWidth",
        currentValue: 1.2,
        idealValue: 1.0,
        figmaBacked: true,
        mutable: true,
        tokenRef: tokenRefs["style.strokeWidth"],
      },
      {
        path: "/style/color",
        currentValue: "#C79A39",
        idealValue: "#C89B3C",
        figmaBacked: true,
        mutable: true,
        tokenRef: tokenRefs["style.color"],
      },
    ],
    autoFixAllowed: canAutoFix("SOFT_PROJECT", ["SOFT_PROJECT", "FIGMA_TOKEN_REALIGNMENT"]),
    status: "pending",
    lastAuditId: null,
  };
}

export function buildPamSeedLane(): PamRuntimeLane {
  return {
    candidate: buildPamSeedCandidate(),
    audits: [],
  };
}
