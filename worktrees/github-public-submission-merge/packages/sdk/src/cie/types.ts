export interface KernelTokenV1 {
  schema_version: "kernel_token.v1";
  world_id: string;
  capsule_digest: string;
  merkle_root: string;
  tick_count: number;
}

export interface InvariantSetV1 {
  schema_version: "invariant_set.v1";
  world_id: string;
  capsule_digest: string;
  merkle_root: string;
  tick_count: number;
  invariants: {
    kinematics: { max_velocity: number; mean_velocity: number };
    stability: { slip_variance: number; stability_score: number };
    control: { input_entropy: number };
    boundary: { min_track_clearance: number };
    energy: { total_joules: number };
  };
  attestation: { extractor_version: string; timestamp: number };
}

export interface CapsuleRef {
  kind: "s3" | "gcs" | "file" | "http" | "ipfs";
  uri: string;
}

export interface CieV2PlugV1 {
  schema_version: "cie_v2_plug.v1";
  world_id: string;
  capsule_digest: string;
  engine_hash: string;
  baseline_merkle_root: string;
  kernel_token: KernelTokenV1;
  invariant_set: InvariantSetV1;
  extractor_version: string;
  capsule_ref?: CapsuleRef;
}
