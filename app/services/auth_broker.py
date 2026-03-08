"""Auth broker for OpenAI claim synthesis, RBAC JWT minting, and Gemini auth."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any
import urllib.parse
import urllib.request

import jwt

from rbac.token_service import RBACJWTIssuer, token_fingerprint
from schemas.handshake import RbacClaimProposal


class AuthBrokerError(RuntimeError):
    """Raised when handshake exchange auth steps fail."""


@dataclass(frozen=True)
class GeminiAccessToken:
    """Gemini token payload returned by Google OAuth endpoint."""

    access_token: str
    token_type: str
    expires_in: int


class OpenAICodexClaimSynthesizer:
    """Generate structured RBAC claim proposals using OpenAI Codex base models."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        endpoint: str = "https://api.openai.com/v1/chat/completions",
        timeout_seconds: int = 30,
    ) -> None:
        self.api_key = (api_key or os.getenv("OPENAI_API_KEY", "")).strip()
        self.model = (model or os.getenv("OPENAI_CODEX_MODEL", "gpt-5-codex")).strip()
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def synthesize(
        self,
        *,
        tenant_id: str,
        client_id: str,
        avatar_id: str,
        requested_scopes: list[str],
        requested_tools: list[str],
        ttl_seconds: int,
    ) -> RbacClaimProposal:
        payload = {
            "tenant_id": tenant_id,
            "client_id": client_id,
            "avatar_id": avatar_id,
            "requested_scopes": sorted(set(requested_scopes)),
            "requested_tools": sorted(set(requested_tools)),
            "ttl_seconds": ttl_seconds,
        }

        if not self.api_key:
            return self._fallback(payload)

        try:
            raw = self._request_openai(payload)
            proposal_data = self._parse_json_object(raw)
        except Exception as exc:  # noqa: BLE001
            raise AuthBrokerError(f"OpenAI claim synthesis failed: {exc}") from exc

        proposal_data.setdefault("tenant_id", tenant_id)
        proposal_data.setdefault("client_id", client_id)
        proposal_data.setdefault("avatar_id", avatar_id)
        proposal_data.setdefault("roles", ["pipeline_operator"])
        proposal_data.setdefault("scopes", requested_scopes)
        proposal_data.setdefault("tools", requested_tools)
        proposal_data.setdefault("ttl_seconds", ttl_seconds)
        proposal_data.setdefault("reason", "OpenAI Codex synthesized RBAC claim proposal.")
        proposal_data.setdefault("source", "openai-codex")
        return RbacClaimProposal.model_validate(proposal_data)

    def _request_openai(self, payload: dict[str, Any]) -> str:
        system_prompt = (
            "You are an RBAC policy synthesis engine. "
            "Return a JSON object only with fields: tenant_id, client_id, avatar_id, "
            "roles (array), scopes (array), tools (array), ttl_seconds (int), reason (string), source (string). "
            "Never include markdown."
        )
        request_payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=True)},
            ],
        }
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(request_payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as response:  # noqa: S310
            body = json.loads(response.read().decode("utf-8"))
        return str(body["choices"][0]["message"]["content"])

    @staticmethod
    def _parse_json_object(raw: str) -> dict[str, Any]:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = [line for line in cleaned.splitlines() if not line.startswith("```")]
            cleaned = "\n".join(lines).strip()
        parsed = json.loads(cleaned)
        if not isinstance(parsed, dict):
            raise ValueError("OpenAI response must be a JSON object")
        return parsed

    @staticmethod
    def _fallback(payload: dict[str, Any]) -> RbacClaimProposal:
        roles = ["pipeline_operator"]
        requested_scopes = list(payload.get("requested_scopes", []))
        requested_tools = list(payload.get("requested_tools", []))
        if any(scope.startswith("mcp:admin") for scope in requested_scopes):
            roles = ["admin"]
        return RbacClaimProposal(
            tenant_id=str(payload["tenant_id"]),
            client_id=str(payload["client_id"]),
            avatar_id=str(payload["avatar_id"]),
            roles=roles,
            scopes=sorted(set(requested_scopes or ["mcp:handshake", "world:model:read"])),
            tools=sorted(set(requested_tools)),
            ttl_seconds=int(payload["ttl_seconds"]),
            reason="Local deterministic fallback used because OPENAI_API_KEY is not configured.",
            source="local-fallback",
        )


class ClaimPolicyValidator:
    """Validate synthesized RBAC claims against local policy constraints."""

    _ROLE_ALLOWLIST = {"admin", "pipeline_operator", "healer", "observer"}
    _SCOPE_PATTERN = re.compile(r"^[a-zA-Z0-9:_\-/\.]+$")
    _TOOL_PATTERN = re.compile(r"^[a-zA-Z0-9:_\-/\.]+$")

    def validate(
        self,
        proposal: RbacClaimProposal,
        *,
        requested_scopes: list[str],
        requested_tools: list[str],
    ) -> RbacClaimProposal:
        if not proposal.client_id.strip() or not proposal.avatar_id.strip() or not proposal.tenant_id.strip():
            raise AuthBrokerError("Claim proposal missing tenant/client/avatar identifiers")

        roles = sorted(set(proposal.roles))
        if not roles:
            raise AuthBrokerError("Claim proposal must include at least one role")
        if any(role not in self._ROLE_ALLOWLIST for role in roles):
            raise AuthBrokerError("Claim proposal contains unsupported role")

        normalized_scopes = sorted(set(proposal.scopes))
        if any(not self._SCOPE_PATTERN.match(scope) for scope in normalized_scopes):
            raise AuthBrokerError("Claim proposal includes invalid scope format")
        allowed_scopes = set(requested_scopes) | {"mcp:handshake", "world:model:read", "workflow:map:read"}
        if requested_scopes and any(scope not in allowed_scopes for scope in normalized_scopes):
            raise AuthBrokerError("Claim proposal includes unrequested scopes")

        normalized_tools = sorted(set(proposal.tools))
        if any(not self._TOOL_PATTERN.match(tool) for tool in normalized_tools):
            raise AuthBrokerError("Claim proposal includes invalid tool format")
        if requested_tools and any(tool not in set(requested_tools) for tool in normalized_tools):
            raise AuthBrokerError("Claim proposal includes unrequested tools")

        ttl = max(60, min(int(proposal.ttl_seconds), 3600))
        return proposal.model_copy(
            update={
                "roles": roles,
                "scopes": normalized_scopes,
                "tools": normalized_tools,
                "ttl_seconds": ttl,
            }
        )


class GeminiServiceAccountTokenProvider:
    """Acquire Gemini access token via Google service-account OAuth flow."""

    def __init__(self, *, token_endpoint: str = "https://oauth2.googleapis.com/token", timeout_seconds: int = 30) -> None:
        self.token_endpoint = token_endpoint
        self.timeout_seconds = timeout_seconds

    def get_access_token(self, *, scopes: list[str]) -> GeminiAccessToken:
        account = self._load_service_account()
        now = int(datetime.now(timezone.utc).timestamp())
        assertion = self._build_assertion(account, scopes=scopes, now=now)
        body = urllib.parse.urlencode(
            {
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            self.token_endpoint,
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:  # noqa: S310
                payload = json.loads(response.read().decode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise AuthBrokerError(f"Gemini service-account token request failed: {exc}") from exc

        access_token = str(payload.get("access_token", "")).strip()
        token_type = str(payload.get("token_type", "Bearer")).strip() or "Bearer"
        expires_in = int(payload.get("expires_in", 0))
        if not access_token:
            raise AuthBrokerError("Google OAuth response did not include access_token")
        return GeminiAccessToken(access_token=access_token, token_type=token_type, expires_in=expires_in)

    @staticmethod
    def _load_service_account() -> dict[str, Any]:
        inline_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
        if inline_json:
            try:
                account = json.loads(inline_json)
            except json.JSONDecodeError as exc:
                raise AuthBrokerError("GOOGLE_SERVICE_ACCOUNT_JSON is invalid JSON") from exc
        else:
            path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
            if not path:
                raise AuthBrokerError("Service-account credentials are required for Gemini auth")
            credential_path = Path(path)
            if not credential_path.exists():
                raise AuthBrokerError(f"Service-account credential file not found: {credential_path}")
            account = json.loads(credential_path.read_text(encoding="utf-8"))

        for key in ("client_email", "private_key"):
            if not str(account.get(key, "")).strip():
                raise AuthBrokerError(f"Service-account credentials missing '{key}'")
        return account

    def _build_assertion(self, account: dict[str, Any], *, scopes: list[str], now: int) -> str:
        scope_str = " ".join(sorted(set(scopes)))
        if not scope_str:
            raise AuthBrokerError("At least one Google OAuth scope is required")
        payload = {
            "iss": account["client_email"],
            "scope": scope_str,
            "aud": self.token_endpoint,
            "iat": now,
            "exp": now + 3600,
        }
        headers = {"typ": "JWT"}
        if account.get("private_key_id"):
            headers["kid"] = account["private_key_id"]
        try:
            return jwt.encode(payload, account["private_key"], algorithm="RS256", headers=headers)
        except Exception as exc:  # noqa: BLE001
            raise AuthBrokerError(f"Failed to build Google OAuth assertion: {exc}") from exc


class A2AAuthBroker:
    """Coordinate OpenAI claim synthesis, RBAC JWT minting, and Gemini auth."""

    def __init__(
        self,
        *,
        synthesizer: OpenAICodexClaimSynthesizer | None = None,
        validator: ClaimPolicyValidator | None = None,
        rbac_issuer: RBACJWTIssuer | None = None,
        gemini_provider: GeminiServiceAccountTokenProvider | None = None,
    ) -> None:
        self._synthesizer = synthesizer or OpenAICodexClaimSynthesizer()
        self._validator = validator or ClaimPolicyValidator()
        self._rbac_issuer = rbac_issuer or RBACJWTIssuer()
        self._gemini_provider = gemini_provider or GeminiServiceAccountTokenProvider()

    def exchange(
        self,
        *,
        tenant_id: str,
        client_id: str,
        avatar_id: str,
        requested_scopes: list[str],
        requested_tools: list[str],
        ttl_seconds: int,
    ) -> dict[str, Any]:
        proposal = self._synthesizer.synthesize(
            tenant_id=tenant_id,
            client_id=client_id,
            avatar_id=avatar_id,
            requested_scopes=requested_scopes,
            requested_tools=requested_tools,
            ttl_seconds=ttl_seconds,
        )
        proposal = self._validator.validate(
            proposal,
            requested_scopes=requested_scopes,
            requested_tools=requested_tools,
        )
        token, claims = self._rbac_issuer.issue_access_token(
            {
                "sub": f"{proposal.client_id}:{proposal.avatar_id}",
                "tenant_id": proposal.tenant_id,
                "client_id": proposal.client_id,
                "avatar_id": proposal.avatar_id,
                "roles": proposal.roles,
                "scopes": proposal.scopes,
                "tools": proposal.tools,
            },
            ttl_seconds=proposal.ttl_seconds,
        )
        gemini = self._gemini_provider.get_access_token(
            scopes=[
                "https://www.googleapis.com/auth/cloud-platform",
                "https://www.googleapis.com/auth/generative-language",
            ]
        )

        rbac_fp = token_fingerprint(token)
        gemini_fp = token_fingerprint(gemini.access_token)
        return {
            "claim_proposal": proposal,
            "rbac_access_token": token,
            "rbac_claims": claims,
            "rbac_token_ref": f"rbac://jwt/{rbac_fp}",
            "rbac_token_fingerprint": rbac_fp,
            "gemini_access_token": gemini.access_token,
            "gemini_token_ref": f"gemini://sa/{gemini_fp}",
            "gemini_token_fingerprint": gemini_fp,
            "gemini_expires_in": gemini.expires_in,
        }

