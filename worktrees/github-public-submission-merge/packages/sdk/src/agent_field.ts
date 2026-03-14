export type CanonPolicy = { json: "JCS"; unicode: "NFC" };

export type EncapsulatedRuntimeBlockV1 = {
  v: 1;
  block_id: string;
  preface: { preface_id: string; preface_sha256: string };
  source_cid: {
    cid: string;
    cidv: 0 | 1;
    base: "base32" | "base58btc";
    codec: string;
    multihash: { name: string; bits: number; digest_hex: `0x${string}` };
  };
  input_binding: { external_config_sha256: string; normalization: CanonPolicy };
  tensor_spec: { name: string; dims: number; dtype: "f32" | "f16" | "i32"; layout: "row_major" };
  agent_field: {
    agent_id: string;
    role: string;
    state_machine_protocol: {
      protocol_id: string;
      embedding_gate: { gate_id: string; policy: "fail_closed" };
    };
  };
  runtime_calls: Array<{
    method: "POST";
    path: string;
    request_sha256: string;
    response_sha256: string;
  }>;
  receipts: { ledger_chain: { prev_hash: string; hash: string }; qube_digest: string };
};
