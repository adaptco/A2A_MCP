import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
    CallToolRequestSchema,
    ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import process from "process";

/**
 * JulesHostServer provides a specialized MCP server for CFO-related field engine tasks.
 * It handles financial data processing and reporting logic.
 */
export class JulesHostServer {
    private server: Server;
    private connected = false;

    constructor() {
        this.server = new Server(
            {
                name: "fieldengine-cfo-mcp",
                version: "0.1.0",
            },
            {
                capabilities: {
                    tools: {},
                },
            }
        );

        this.setupToolHandlers();

        this.server.onerror = (error: any) => console.error("[MCP Error]", error);
        process.on("SIGINT", async () => {
            await this.server.close();
            this.connected = false;
            process.exit(0);
        });

        void this.start();
    }

    public async start() {
        if (this.connected) {
            return;
        }

        const transport = new StdioServerTransport();
        await this.server.connect(transport);
        this.connected = true;
    }

    public async start() {
        if (this.connected) {
            return;
        }

        const transport = new StdioServerTransport();
        await this.server.connect(transport);
        this.connected = true;
    }

    private setupToolHandlers() {
        this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
            tools: [
                {
                    name: "analyze_financial_metrics",
                    description: "Analyzes key financial metrics for field operations",
                    inputSchema: {
                        type: "object",
                        properties: {
                            period: { type: "string", description: "Reporting period (e.g., Q1, 2023)" },
                            departmentId: { type: "string" }
                        },
                        required: ["period"]
                    }
                }
            ]
        }));

        this.server.setRequestHandler(CallToolRequestSchema, async (request: any) => {
            if (request.params.name === "analyze_financial_metrics") {
                // Implementation logic for financial analysis
                return {
                    content: [
                        {
                            type: "text",
                            text: "Financial analysis completed for the specified period."
                        }
                    ]
                };
            }
            throw new Error(`Tool not found: ${request.params.name}`);
        });
    }
}
