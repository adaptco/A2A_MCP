import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

import { leverage_capacity_sensitivity } from "../tools/capital/leverage_capacity_sensitivity.js";
import { earnings_vol_sensitivity } from "../tools/capital/earnings_vol_sensitivity.js";
import { cv_projection } from "../tools/capital/cv_projection.js";
import { cost_of_capital_delta } from "../tools/capital/cost_of_capital_delta.js";

import { tighten_thresholds } from "../tools/drift/tighten_thresholds.js";
import { drift_heatmap } from "../tools/drift/drift_heatmap.js";
import { compute_drift_index } from "../tools/drift/compute_drift_index.js";

import { read_transactions } from "../tools/netsuite/read_transactions.js";
import { write_flags } from "../tools/netsuite/write_flags.js";

import { expire_override } from "../tools/overrides/expire_override.js";
import { submit_override } from "../tools/overrides/submit_override.js";
import { approve_override } from "../tools/overrides/approve_override.js";
import { renew_override } from "../tools/overrides/renew_override.js";

import { export_audit_bundle } from "../tools/audit/export_audit_bundle.js";
import { replay_package } from "../tools/audit/replay_package.js";

import { journalSchemaResource } from "../resources/schemas/journal_schema.resource.js";
import { overrideSchemaResource } from "../resources/schemas/override_schema.resource.js";
import { policyHistoryResource } from "../resources/policy/policy_history.resource.js";
import { currentPolicyResource } from "../resources/policy/current_policy.resource.js";
import { driftDashboardResource } from "../resources/dashboards/drift_dashboard.resource.js";

export const startServer = async (): Promise<void> => {
  const server = new McpServer({
    name: "fieldengine-cfo-mcp",
    version: "0.1.0"
  });

  // Tools
  server.tool("leverage_capacity_sensitivity", {}, async (args) => {
    const result = await leverage_capacity_sensitivity(args);
    return { content: [{ type: "text", text: JSON.stringify(result) }] };
  });
  server.tool("earnings_vol_sensitivity", {}, async (args) => {
    const result = await earnings_vol_sensitivity(args);
    return { content: [{ type: "text", text: JSON.stringify(result) }] };
  });
  server.tool("cv_projection", {}, async (args) => {
    const result = await cv_projection(args);
    return { content: [{ type: "text", text: JSON.stringify(result) }] };
  });
  server.tool("cost_of_capital_delta", {}, async (args) => {
    const result = await cost_of_capital_delta(args);
    return { content: [{ type: "text", text: JSON.stringify(result) }] };
  });

  server.tool("tighten_thresholds", {}, async (args) => {
    const result = await tighten_thresholds(args);
    return { content: [{ type: "text", text: JSON.stringify(result) }] };
  });
  server.tool("drift_heatmap", {}, async (args) => {
    const result = await drift_heatmap(args);
    return { content: [{ type: "text", text: JSON.stringify(result) }] };
  });
  server.tool("compute_drift_index", {}, async (args) => {
    const result = await compute_drift_index(args);
    return { content: [{ type: "text", text: JSON.stringify(result) }] };
  });

  server.tool("read_transactions", {}, async (args) => {
    const result = await read_transactions(args);
    return { content: [{ type: "text", text: JSON.stringify(result) }] };
  });
  server.tool("write_flags", {}, async (args) => {
    const result = await write_flags(args);
    return { content: [{ type: "text", text: JSON.stringify(result) }] };
  });

  server.tool("expire_override", {}, async (args) => {
    const result = await expire_override(args);
    return { content: [{ type: "text", text: JSON.stringify(result) }] };
  });
  server.tool("submit_override", {}, async (args) => {
    const result = await submit_override(args);
    return { content: [{ type: "text", text: JSON.stringify(result) }] };
  });
  server.tool("approve_override", {}, async (args) => {
    const result = await approve_override(args);
    return { content: [{ type: "text", text: JSON.stringify(result) }] };
  });
  server.tool("renew_override", {}, async (args) => {
    const result = await renew_override(args);
    return { content: [{ type: "text", text: JSON.stringify(result) }] };
  });

  server.tool("export_audit_bundle", {}, async (args) => {
    const result = await export_audit_bundle(args);
    return { content: [{ type: "text", text: JSON.stringify(result) }] };
  });
  server.tool("replay_package", {}, async (args) => {
    const result = await replay_package(args);
    return { content: [{ type: "text", text: JSON.stringify(result) }] };
  });

  // Resources
  server.resource(journalSchemaResource.uri, journalSchemaResource.uri, async (uri) => ({
    contents: [{
      uri: uri.href,
      text: JSON.stringify(await journalSchemaResource.read())
    }]
  }));

  server.resource(overrideSchemaResource.uri, overrideSchemaResource.uri, async (uri) => ({
    contents: [{
      uri: uri.href,
      text: JSON.stringify(await overrideSchemaResource.read())
    }]
  }));

  server.resource(policyHistoryResource.uri, policyHistoryResource.uri, async (uri) => ({
    contents: [{
      uri: uri.href,
      text: JSON.stringify(await policyHistoryResource.read())
    }]
  }));

  server.resource(currentPolicyResource.uri, currentPolicyResource.uri, async (uri) => ({
    contents: [{
      uri: uri.href,
      text: JSON.stringify(await currentPolicyResource.read())
    }]
  }));

  server.resource(driftDashboardResource.uri, driftDashboardResource.uri, async (uri) => ({
    contents: [{
      uri: uri.href,
      text: JSON.stringify(await driftDashboardResource.read())
    }]
  }));

  const transport = new StdioServerTransport();
  await server.connect(transport);
};

// Start the server directly
if (import.meta.url === `file://${process.argv[1]}`) {
  startServer().catch((error) => {
    console.error("Server error:", error);
    process.exit(1);
  });
}
