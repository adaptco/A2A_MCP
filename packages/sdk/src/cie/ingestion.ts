import Ajv from "ajv";
import plugSchema from "../schemas/cie_v2_plug.v1.schema.json";
import invariantSchema from "../schemas/invariant_set.v1.schema.json";
import { CieV2PlugV1, InvariantSetV1, KernelTokenV1 } from "./types";

const ajv = new Ajv({ allErrors: true, strict: true });
ajv.addSchema(invariantSchema as any, "invariant_set.v1.schema.json");
const validatePlug = ajv.compile<CieV2PlugV1>(plugSchema as any);
const validateInvariant = ajv.compile<InvariantSetV1>(invariantSchema as any);

export interface AgentContext {
  world_id: string;
  capsule_digest: string;
  engine_hash: string;
  psp: string;
  kernel_token: KernelTokenV1;
  invariants: InvariantSetV1;
  capsule_ref?: { kind: string; uri: string };
}

export function ingestPlug(raw: unknown): AgentContext {
  if (!validatePlug(raw)) {
    throw new Error(
      "cie_v2_plug.v1 validation failed: " + ajv.errorsText(validatePlug.errors, { separator: "\n" }),
    );
  }
  const plug = raw as CieV2PlugV1;

  if (!validateInvariant(plug.invariant_set)) {
    throw new Error(
      "invariant_set.v1 validation failed: " +
        ajv.errorsText(validateInvariant.errors, { separator: "\n" }),
    );
  }

  if (plug.kernel_token.capsule_digest !== plug.capsule_digest) {
    throw new Error("kernel_token.capsule_digest mismatch");
  }
  if (plug.kernel_token.merkle_root !== plug.baseline_merkle_root) {
    throw new Error("kernel_token.merkle_root != baseline_merkle_root");
  }
  if (plug.invariant_set.merkle_root !== plug.baseline_merkle_root) {
    throw new Error("invariant_set.merkle_root != baseline_merkle_root");
  }

  return {
    world_id: plug.world_id,
    capsule_digest: plug.capsule_digest,
    engine_hash: plug.engine_hash,
    psp: plug.baseline_merkle_root,
    kernel_token: plug.kernel_token,
    invariants: plug.invariant_set,
    capsule_ref: plug.capsule_ref,
  };
}
