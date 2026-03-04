use serde::Deserialize;

#[derive(Debug, Deserialize)]
pub struct KernelTokenV1 {
    pub schema_version: String,
    pub world_id: String,
    pub capsule_digest: String,
    pub merkle_root: String,
    pub tick_count: u64,
}

#[derive(Debug, Deserialize)]
pub struct InvariantSetV1 {
    pub schema_version: String,
    pub world_id: String,
    pub capsule_digest: String,
    pub merkle_root: String,
    pub tick_count: u64,
    pub invariants: serde_json::Value,
    pub attestation: serde_json::Value,
}

#[derive(Debug, Deserialize)]
pub struct CapsuleRef {
    pub kind: String,
    pub uri: String,
}

#[derive(Debug, Deserialize)]
pub struct CieV2PlugV1 {
    pub schema_version: String,
    pub world_id: String,
    pub capsule_digest: String,
    pub engine_hash: String,
    pub baseline_merkle_root: String,
    pub kernel_token: KernelTokenV1,
    pub invariant_set: InvariantSetV1,
    pub extractor_version: String,
    pub capsule_ref: Option<CapsuleRef>,
}

pub struct AgentContext {
    pub world_id: String,
    pub capsule_digest: String,
    pub engine_hash: String,
    pub psp: String,
    pub kernel_token: KernelTokenV1,
    pub invariants: InvariantSetV1,
    pub capsule_ref: Option<CapsuleRef>,
}

pub fn ingest_plug(json: &str) -> anyhow::Result<AgentContext> {
    let plug: CieV2PlugV1 = serde_json::from_str(json)?;

    if plug.schema_version != "cie_v2_plug.v1" {
        anyhow::bail!("unsupported schema_version");
    }
    if plug.kernel_token.capsule_digest != plug.capsule_digest {
        anyhow::bail!("kernel_token.capsule_digest mismatch");
    }
    if plug.kernel_token.merkle_root != plug.baseline_merkle_root {
        anyhow::bail!("kernel_token.merkle_root != baseline_merkle_root");
    }
    if plug.invariant_set.merkle_root != plug.baseline_merkle_root {
        anyhow::bail!("invariant_set.merkle_root != baseline_merkle_root");
    }

    Ok(AgentContext {
        world_id: plug.world_id,
        capsule_digest: plug.capsule_digest,
        engine_hash: plug.engine_hash,
        psp: plug.baseline_merkle_root,
        kernel_token: plug.kernel_token,
        invariants: plug.invariant_set,
        capsule_ref: plug.capsule_ref,
    })
}
