import { McpServer } from './mcp_server.js';
import { read_transactions } from '../tools/netsuite/read_transactions.js';
import { write_flags } from '../tools/netsuite/write_flags.js';
import { compute_drift_index } from '../tools/drift/compute_drift_index.js';
import { currentPolicyResource } from '../resources/policy/current_policy.resource.js';
import { policyHistoryResource } from '../resources/policy/policy_history.resource.js';

export const startServer = async (): Promise<void> => {
  const server = new McpServer();

  // --- Register Tools ---

  // NetSuite Tools
  server.registerTool({
    name: 'read_transactions',
    description: 'Read transactions from NetSuite (Stubbed)',
    inputSchema: { type: 'object', additionalProperties: true },
    handler: read_transactions,
  });

  server.registerTool({
    name: 'write_flags',
    description: 'Write flags to NetSuite (Stubbed)',
    inputSchema: { type: 'object', additionalProperties: true },
    handler: write_flags,
  });

  // Drift Tools
  server.registerTool({
    name: 'compute_drift_index',
    description: 'Compute drift index (Stubbed)',
    inputSchema: { type: 'object', properties: { index: { type: 'number' } }, required: ['index'] },
    handler: compute_drift_index,
  });

  // --- Register Resources ---

  server.registerResource({
    uri: currentPolicyResource.uri,
    name: 'Current Policy',
    mimeType: 'application/json',
    read: currentPolicyResource.read,
  });

  server.registerResource({
    uri: policyHistoryResource.uri,
    name: 'Policy History',
    mimeType: 'application/json',
    read: policyHistoryResource.read,
  });

  // --- Register Prompts ---

  server.registerPrompt({
    name: 'cfo_decision_support',
    description: 'CFO Decision Support Prompt',
    arguments: [
        { name: 'context', description: 'Decision context', required: true }
    ],
    get: async (args) => {
        return {
            messages: [
                {
                    role: 'user',
                    content: {
                        type: 'text',
                        text: `Analyze the following context for CFO decision support: ${args?.context || ''}`
                    }
                }
            ]
        };
    }
  });

  server.start();
};

// Execute if run directly
if (import.meta.url === `file://${process.argv[1]}`) {
  startServer().catch(console.error);
}
