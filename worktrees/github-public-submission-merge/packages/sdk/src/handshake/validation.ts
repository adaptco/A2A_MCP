import AjvModule from "ajv";
const Ajv = ( AjvModule as any ).default || AjvModule;
import handshakeBoundSchema from "../schemas/handshake_bound.v1.schema.json" with { type: "json" };
import handshakeRefusalSchema from "../schemas/handshake_refusal.v1.schema.json" with { type: "json" };
import handshakeRequestSchema from "../schemas/handshake_request.v1.schema.json" with { type: "json" };
import handshakeRevokedSchema from "../schemas/handshake_revoked.v1.schema.json" with { type: "json" };
import {
  HandshakeBoundV1,
  HandshakeRefusalV1,
  HandshakeRequestV1,
  HandshakeRevokedV1,
} from "./types.js";

const ajv: any = new ( Ajv as any )( { allErrors: true, strict: true } );

export const validateHandshakeRequestV1: any = ( ajv as any ).compile(
  handshakeRequestSchema as any,
);
export const validateHandshakeBoundV1: any = ( ajv as any ).compile( handshakeBoundSchema as any );
export const validateHandshakeRevokedV1: any = ( ajv as any ).compile(
  handshakeRevokedSchema as any,
);
export const validateHandshakeRefusalV1: any = ( ajv as any ).compile(
  handshakeRefusalSchema as any,
);

export function validateHandshakeRequest ( raw: unknown ): HandshakeRequestV1 {
  if ( !validateHandshakeRequestV1( raw ) )
  {
    throw new Error(
      "handshake_request.v1 validation failed: " +
      ajv.errorsText( validateHandshakeRequestV1.errors, { separator: "\n" } ),
    );
  }

  return raw as HandshakeRequestV1;
}
