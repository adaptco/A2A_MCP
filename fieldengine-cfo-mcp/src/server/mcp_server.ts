import { Readable, Writable } from 'node:stream';
import { EventEmitter } from 'node:events';

// Types for MCP
export interface McpTool {
  name: string;
  description?: string;
  inputSchema: Record<string, unknown>;
  handler: (args: any) => Promise<any>;
}

export interface McpResource {
  uri: string;
  name?: string;
  description?: string;
  mimeType?: string;
  read: () => Promise<any>;
}

export interface McpPrompt {
  name: string;
  description?: string;
  arguments?: { name: string; description?: string; required?: boolean }[];
  get: (args?: Record<string, string>) => Promise<{ messages: { role: string; content: { type: string; text: string } }[] }>;
}

export class McpServer extends EventEmitter {
  private tools: Map<string, McpTool> = new Map();
  private resources: Map<string, McpResource> = new Map();
  private prompts: Map<string, McpPrompt> = new Map();

  constructor() {
    super();
  }

  public registerTool(tool: McpTool) {
    this.tools.set(tool.name, tool);
  }

  public registerResource(resource: McpResource) {
    this.resources.set(resource.uri, resource);
  }

  public registerPrompt(prompt: McpPrompt) {
    this.prompts.set(prompt.name, prompt);
  }

  public start() {
    process.stdin.setEncoding('utf8');
    let buffer = '';

    process.stdin.on('data', async (chunk) => {
      buffer += chunk;
      let newlineIndex;
      while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
        const line = buffer.slice(0, newlineIndex);
        buffer = buffer.slice(newlineIndex + 1);
        if (line.trim()) {
          await this.handleMessage(line);
        }
      }
    });

    // Send an initialization message to stderr to indicate startup (optional but helpful for debugging)
    console.error('MCP Server started on stdio');
  }

  private async handleMessage(message: string) {
    let request: any;
    try {
      request = JSON.parse(message);
    } catch (e) {
      console.error('Failed to parse JSON-RPC message:', e);
      return;
    }

    if (!request.id) {
        // Notifications are ignored
        return;
    }

    try {
      const result = await this.dispatch(request.method, request.params);
      this.sendResponse({
        jsonrpc: '2.0',
        result,
        id: request.id,
      });
    } catch (error: any) {
      this.sendResponse({
        jsonrpc: '2.0',
        error: {
          code: error.code || -32603,
          message: error.message || 'Internal error',
          data: error.data,
        },
        id: request.id,
      });
    }
  }

  private async dispatch(method: string, params: any): Promise<any> {
    switch (method) {
      case 'initialize':
        return {
          protocolVersion: '2024-11-05',
          capabilities: {
            tools: {},
            resources: {},
            prompts: {},
          },
          serverInfo: {
            name: 'fieldengine-cfo-mcp',
            version: '0.1.0',
          },
        };

      case 'tools/list':
        return {
          tools: Array.from(this.tools.values()).map(t => ({
            name: t.name,
            description: t.description,
            inputSchema: t.inputSchema,
          })),
        };

      case 'tools/call':
        const toolName = params.name;
        const tool = this.tools.get(toolName);
        if (!tool) {
          throw { code: -32601, message: 'Method not found (tool not registered)' };
        }

        try {
            const result = await tool.handler(params.arguments || {});
            return {
                content: [
                    {
                        type: 'text',
                        text: JSON.stringify(result, null, 2)
                    }
                ]
            };
        } catch (e: any) {
            throw { code: -32000, message: e.message };
        }

      case 'resources/list':
        return {
          resources: Array.from(this.resources.values()).map(r => ({
            uri: r.uri,
            name: r.name,
            description: r.description,
            mimeType: r.mimeType,
          })),
        };

      case 'resources/read':
        const resourceUri = params.uri;
        const resource = this.resources.get(resourceUri);
        if (!resource) {
            throw { code: -32601, message: 'Resource not found' };
        }
        try {
            const content = await resource.read();
            return {
                contents: [
                    {
                        uri: resourceUri,
                        mimeType: resource.mimeType || 'application/json',
                        text: typeof content === 'string' ? content : JSON.stringify(content, null, 2)
                    }
                ]
            };
        } catch (e: any) {
             throw { code: -32000, message: e.message };
        }

      case 'prompts/list':
        return {
          prompts: Array.from(this.prompts.values()).map(p => ({
            name: p.name,
            description: p.description,
            arguments: p.arguments,
          })),
        };

      case 'prompts/get':
         const promptName = params.name;
         const prompt = this.prompts.get(promptName);
         if (!prompt) {
             throw { code: -32601, message: 'Prompt not found' };
         }
         return await prompt.get(params.arguments);

      case 'ping':
        return {};

      default:
        throw { code: -32601, message: 'Method not found' };
    }
  }

  private sendResponse(response: any) {
    process.stdout.write(JSON.stringify(response) + '\n');
  }
}
