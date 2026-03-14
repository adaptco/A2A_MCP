export type PamSeverity =
  | "HARD_REJECT"
  | "DISCRETE_INVARIANT"
  | "SOFT_PROJECT"
  | "CONTINUOUS_DEVIATION";

export type PamRequestType = "BLUEPRINT_RE_SKETCH";
export type PamPatchOperation = "replace";
export type PamAuditAction = "AUTO_FIX" | "ESCALATE_HITL";
export type PamVerificationStatus = "PASS" | "FAIL";
export type PamCandidateStatus = "pending" | "patched" | "escalated";

export interface PamJsonPatchOperation {
  op: PamPatchOperation;
  path: string;
  value: unknown;
}

export interface PamDriftInput {
  path: string;
  currentValue: unknown;
  idealValue: unknown;
  figmaBacked: boolean;
  mutable: boolean;
  tokenRef?: string;
}

export interface PamVerificationResult {
  ok: boolean;
  remainingViolations: string[];
  driftScoreBefore: number;
  driftScoreAfter: number;
}

export interface PamTokenRefs {
  [path: string]: string;
}

export interface PamAutoFixCandidate {
  requestType: PamRequestType;
  nodeId: string;
  violationId: string;
  severity: PamSeverity;
  violationCodes: string[];
  componentId?: string;
  telemetrySnapshotId: string;
  figmaSyncVersion: string;
  currentState: Record<string, unknown>;
  idealState: Record<string, unknown>;
  tokenRefs: PamTokenRefs;
  driftInputs: PamDriftInput[];
  autoFixAllowed: boolean;
  status: PamCandidateStatus;
  lastAuditId?: string | null;
}

export interface PamAuditEntry {
  auditId: string;
  taskRef: string;
  requestType: PamRequestType;
  nodeId: string;
  violationId: string;
  severity: PamSeverity;
  action: PamAuditAction;
  prePatchStateHash: string;
  postPatchStateHash: string;
  patchPayload: PamJsonPatchOperation[];
  figmaSyncVersion: string;
  verificationResult: PamVerificationStatus;
  sealed: boolean;
  timestamp: string;
  operatorMode: "AUTO_FIX" | "HITL";
}

export interface PamOrchestratorConfig {
  agent_id: string;
  role: string;
  version: string;
  capabilities: string[];
  policy: {
    auto_fix_enabled: boolean;
    allow_auto_fix_for: PamSeverity[];
    deny_auto_fix_for: string[];
    requires_figma_source_of_truth: boolean;
    requires_patch_audit_trail: boolean;
    requires_post_patch_validation: boolean;
    max_patch_fields_per_operation: number;
    fail_closed_on_missing_token: boolean;
  };
  inputs: {
    required: string[];
    optional: string[];
  };
  decision_table: Record<
    PamSeverity,
    {
      action: "ESCALATE_HITL" | "GENERATE_PATCH";
      patch_allowed: boolean;
    }
  >;
  patch_strategy: {
    format: "json_patch";
    allowed_ops: PamPatchOperation[];
    allowed_paths: string[];
    forbidden_paths: string[];
  };
  verification: {
    re_run_validator: boolean;
    required_outcomes: string[];
    terminal_success_log: string;
    terminal_failure_log: string;
  };
  persistence: {
    seal_to_agentic_tasks: boolean;
    record_fields: string[];
  };
}

export interface PamRuntimeLane {
  candidate: PamAutoFixCandidate | null;
  audits: PamAuditEntry[];
}

export interface PamLaneResponse extends PamRuntimeLane {
  config: PamOrchestratorConfig;
}

export const PAM_AUTO_FIX_ALLOWED = new Set<PamSeverity>([
  "SOFT_PROJECT",
  "CONTINUOUS_DEVIATION",
]);

export const PAM_FORBIDDEN_VIOLATION_CODES = new Set([
  "C5_SYMMETRY_BREAK",
  "FORBIDDEN_GEOMETRY_MUTATION",
]);

export function canAutoFix(
  severity: PamSeverity,
  violationCodes: string[],
): boolean {
  if (!PAM_AUTO_FIX_ALLOWED.has(severity)) {
    return false;
  }

  return !violationCodes.some((code) => PAM_FORBIDDEN_VIOLATION_CODES.has(code));
}

export function generateCorrectionPatch(
  items: PamDriftInput[],
): PamJsonPatchOperation[] {
  return items
    .filter((item) => item.figmaBacked && item.mutable)
    .filter((item) => item.currentValue !== item.idealValue)
    .map((item) => ({
      op: "replace",
      path: item.path,
      value: item.idealValue,
    }));
}

export function verifyCorrection(result: PamVerificationResult): boolean {
  return (
    result.ok &&
    result.remainingViolations.length === 0 &&
    result.driftScoreAfter <= result.driftScoreBefore
  );
}
