Required secrets:

- ZAPIER_MCP_TOKEN: Zapier MCP token (never committed)
- ZAPIER_MCP_ENDPOINT: MCP server URL
- PRIVACY_POLICY_URL: must be a public https URL

Policy:
- If PRIVACY_POLICY_URL missing or not https, CI must fail (fail-closed).
- ZAPIER_CI_WEBHOOK_URL: Zapier Catch Hook URL for CI telemetry
