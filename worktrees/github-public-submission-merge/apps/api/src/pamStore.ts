import type { PrismaClient } from "@prisma/client";
import type {
  PamAuditEntry,
  PamAutoFixCandidate,
  PamRuntimeLane,
} from "@world-os/sdk";
import { buildPamSeedCandidate, buildPamSeedLane } from "./pamSeed.js";

export const PRIMARY_PAM_LANE_KEY = "primary";

export interface PamStore {
  getLane(): Promise<PamRuntimeLane>;
  saveExecution(candidate: PamAutoFixCandidate, audit: PamAuditEntry): Promise<PamRuntimeLane>;
}

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function candidateToRecord(candidate: PamAutoFixCandidate) {
  return {
    laneKey: PRIMARY_PAM_LANE_KEY,
    requestType: candidate.requestType,
    nodeId: candidate.nodeId,
    violationId: candidate.violationId,
    severity: candidate.severity,
    violationCodes: clone(candidate.violationCodes),
    componentId: candidate.componentId ?? null,
    telemetrySnapshotId: candidate.telemetrySnapshotId,
    figmaSyncVersion: candidate.figmaSyncVersion,
    currentState: clone(candidate.currentState),
    idealState: clone(candidate.idealState),
    tokenRefs: clone(candidate.tokenRefs),
    driftInputs: clone(candidate.driftInputs),
    autoFixAllowed: candidate.autoFixAllowed,
    status: candidate.status,
    lastAuditId: candidate.lastAuditId ?? null,
  };
}

function auditToRecord(audit: PamAuditEntry) {
  return {
    auditId: audit.auditId,
    laneKey: PRIMARY_PAM_LANE_KEY,
    taskRef: audit.taskRef,
    requestType: audit.requestType,
    nodeId: audit.nodeId,
    violationId: audit.violationId,
    severity: audit.severity,
    action: audit.action,
    prePatchStateHash: audit.prePatchStateHash,
    postPatchStateHash: audit.postPatchStateHash,
    patchPayload: clone(audit.patchPayload),
    figmaSyncVersion: audit.figmaSyncVersion,
    verificationResult: audit.verificationResult,
    sealed: audit.sealed,
    timestamp: new Date(audit.timestamp),
    operatorMode: audit.operatorMode,
  };
}

function recordToCandidate(record: {
  requestType: string;
  nodeId: string;
  violationId: string;
  severity: string;
  violationCodes: unknown;
  componentId: string | null;
  telemetrySnapshotId: string;
  figmaSyncVersion: string;
  currentState: unknown;
  idealState: unknown;
  tokenRefs: unknown;
  driftInputs: unknown;
  autoFixAllowed: boolean;
  status: string;
  lastAuditId: string | null;
}): PamAutoFixCandidate {
  return {
    requestType: record.requestType as PamAutoFixCandidate["requestType"],
    nodeId: record.nodeId,
    violationId: record.violationId,
    severity: record.severity as PamAutoFixCandidate["severity"],
    violationCodes: clone(record.violationCodes as string[]),
    componentId: record.componentId ?? undefined,
    telemetrySnapshotId: record.telemetrySnapshotId,
    figmaSyncVersion: record.figmaSyncVersion,
    currentState: clone(record.currentState as Record<string, unknown>),
    idealState: clone(record.idealState as Record<string, unknown>),
    tokenRefs: clone(record.tokenRefs as Record<string, string>),
    driftInputs: clone(record.driftInputs as PamAutoFixCandidate["driftInputs"]),
    autoFixAllowed: record.autoFixAllowed,
    status: record.status as PamAutoFixCandidate["status"],
    lastAuditId: record.lastAuditId,
  };
}

function recordToAudit(record: {
  auditId: string;
  taskRef: string;
  requestType: string;
  nodeId: string;
  violationId: string;
  severity: string;
  action: string;
  prePatchStateHash: string;
  postPatchStateHash: string;
  patchPayload: unknown;
  figmaSyncVersion: string;
  verificationResult: string;
  sealed: boolean;
  timestamp: Date;
  operatorMode: string;
}): PamAuditEntry {
  return {
    auditId: record.auditId,
    taskRef: record.taskRef,
    requestType: record.requestType as PamAuditEntry["requestType"],
    nodeId: record.nodeId,
    violationId: record.violationId,
    severity: record.severity as PamAuditEntry["severity"],
    action: record.action as PamAuditEntry["action"],
    prePatchStateHash: record.prePatchStateHash,
    postPatchStateHash: record.postPatchStateHash,
    patchPayload: clone(record.patchPayload as PamAuditEntry["patchPayload"]),
    figmaSyncVersion: record.figmaSyncVersion,
    verificationResult: record.verificationResult as PamAuditEntry["verificationResult"],
    sealed: record.sealed,
    timestamp: record.timestamp.toISOString(),
    operatorMode: record.operatorMode as PamAuditEntry["operatorMode"],
  };
}

export class InMemoryPamStore implements PamStore {
  private lane: PamRuntimeLane;

  constructor(initialLane: PamRuntimeLane = buildPamSeedLane()) {
    this.lane = clone(initialLane);
  }

  async getLane(): Promise<PamRuntimeLane> {
    if (!this.lane.candidate) {
      this.lane.candidate = buildPamSeedCandidate();
    }
    return clone(this.lane);
  }

  async saveExecution(
    candidate: PamAutoFixCandidate,
    audit: PamAuditEntry,
  ): Promise<PamRuntimeLane> {
    this.lane.candidate = clone(candidate);
    this.lane.audits = [clone(audit), ...this.lane.audits].slice(0, 12);
    return clone(this.lane);
  }
}

export class PrismaPamStore implements PamStore {
  constructor(private prisma: PrismaClient) {}

  private async ensureCandidate() {
    const existing = await this.prisma.pamCandidate.findUnique({
      where: { laneKey: PRIMARY_PAM_LANE_KEY },
    });

    if (existing) {
      return existing;
    }

    return this.prisma.pamCandidate.create({
      data: candidateToRecord(buildPamSeedCandidate()),
    });
  }

  async getLane(): Promise<PamRuntimeLane> {
    const candidateRecord = await this.ensureCandidate();
    const auditRecords = await this.prisma.pamAudit.findMany({
      where: { laneKey: PRIMARY_PAM_LANE_KEY },
      orderBy: { createdAt: "desc" },
      take: 12,
    });

    return {
      candidate: recordToCandidate(candidateRecord),
      audits: auditRecords.map(recordToAudit),
    };
  }

  async saveExecution(
    candidate: PamAutoFixCandidate,
    audit: PamAuditEntry,
  ): Promise<PamRuntimeLane> {
    await this.prisma.$transaction([
      this.prisma.pamCandidate.upsert({
        where: { laneKey: PRIMARY_PAM_LANE_KEY },
        create: candidateToRecord(candidate),
        update: candidateToRecord(candidate),
      }),
      this.prisma.pamAudit.create({
        data: auditToRecord(audit),
      }),
    ]);

    return this.getLane();
  }
}
