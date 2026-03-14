export interface HandshakeRequestV1 {
  schema_version: "handshake_request.v1";
  request_id: string;
  requested_at: number;
  requester: {
    agent_id: string;
    protocol_version: string;
    nonce: string;
  };
  target: {
    agent_id: string;
    endpoint: string;
  };
  intent: {
    session_id: string;
    scopes: string[];
    expires_at: number;
  };
}

export interface HandshakeBoundV1 {
  schema_version: "handshake_bound.v1";
  request_id: string;
  handshake_id: string;
  bound_at: number;
  binding: {
    requester_agent_id: string;
    target_agent_id: string;
    session_id: string;
    expires_at: number;
  };
}

export interface HandshakeRevokedV1 {
  schema_version: "handshake_revoked.v1";
  request_id: string;
  handshake_id: string;
  revoked_at: number;
  revoked_by: "requester" | "responder" | "system";
  reason_code: string;
  reason: string;
}

export interface HandshakeRefusalV1 {
  schema_version: "handshake_refusal.v1";
  request_id: string;
  refused_at: number;
  refusal: {
    code:
      | "invalid_request"
      | "unsupported_protocol"
      | "unauthorized"
      | "conflict"
      | "rate_limited"
      | "internal_error";
    message: string;
    retryable: boolean;
    details?: {
      field?: string;
      expected?: string;
      received?: string;
    };
  };
}
