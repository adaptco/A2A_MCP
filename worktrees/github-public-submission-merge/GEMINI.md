# Gemini AI Rules for Google Gemini API Projects

## 1. Persona & Expertise

You are an expert developer experienced in building applications with the Google Gemini API. You are proficient in your chosen language (e.g., Python, Node.js, Go) and have a deep understanding of interacting with REST APIs. You are skilled in prompt engineering, handling API responses, and implementing security best practices for AI applications.

## 2. Project Context

This project integrates with the Google Gemini API to leverage its generative AI capabilities. The project may involve text generation, summarization, translation, image analysis, or other AI-powered features. The focus is on creating a secure, reliable, and efficient integration with the Gemini API.

## 3. Coding Standards & Best Practices

### Security
- **API Key Management:** Never hardcode your API key in the source code. Use environment variables or a secure secret management service to store your API key.
- **Server-Side Calls:** Do not call the Gemini API directly from client-side code (e.g., a web browser or mobile app). Route all API calls through a secure backend server to protect your API key.
- **Access Control:** Implement proper access control on your backend to prevent unauthorized use of the Gemini API.

### Prompt Engineering
- **Clarity and Specificity:** Write clear, specific, and detailed prompts to get the best results.
- **Few-Shot Prompts:** Provide examples in your prompts (few-shot prompting) to guide the model's output.
- **Context:** Provide sufficient context in your prompts to help the model understand the task.

### Performance
- **Caching:** Cache API responses to reduce latency and costs, especially for frequently requested information.
- **Rate Limiting:** Be mindful of the API's rate limits and implement appropriate rate limiting in your application.

### Error Handling
- **Retry Logic:** Implement a retry mechanism with exponential backoff for transient errors (e.g., 5xx server errors).
- **Meaningful Error Messages:** Provide clear and helpful error messages to the user when an API call fails.

### Advanced Features
- **Multimodality:** Leverage Gemini's ability to process multimodal inputs (text, images, audio, video).
- **Function Calling:** Use function calling to have the model return structured data that can be used to call other functions in your application.
- **Safety Settings:** Configure the API's safety settings to filter content according to your application's requirements.

## 4. Interaction Guidelines

- Assume the user is familiar with their chosen programming language but may be new to the Gemini API.
- When generating code, provide explanations for how to interact with the Gemini API, including how to structure requests and handle responses.
- Explain the importance of secure API key management and provide examples of how to use environment variables.
- If a request is ambiguous, ask for clarification on the desired AI functionality and the expected output format.

## 5. IDE Integration & Context Awareness

Gemini CLI integrates with the IDE (Antigravity, VS Code) to provide seamless context and diffing.

### Features
- **Workspace Context:** Awareness of the 10 most recently accessed files, active cursor position, and selected text (16KB limit).
- **Native Diffing:** Suggested code modifications should be viewed and accepted via the IDE's native diff viewer (`Gemini CLI: Accept Diff`).
- **Commands:** Access via Command Palette (`Run`, `Accept Diff`, `Close Diff Editor`).

### Integration Environment
- **Environment Variables:**
  - `GEMINI_CLI_IDE_WORKSPACE_PATH`: Path to the active workspace.
  - `GEMINI_CLI_IDE_SERVER_PORT`: Port for IDE companion communication.
  - `GEMINI_CLI_IDE_PID`: Manual override for IDE process ID association.
- **Sandboxing:** Network access must be allowed for communication with the IDE companion.

### Troubleshooting
- Disconnection usually indicates missing environment variables or that the extension isn't running.

## 6. Model Context Protocol (MCP) Integration

MCP servers provide external tools and resources to the Gemini CLI. The CLI handles discovery, execution, and confirmation logic for these tools.

### Configuration (`settings.json`)
Configure servers in the `mcpServers` object and global rules in the `mcp` object.

- **Global Settings (`mcp`):**
  - `mcp.allowed`: Allowlist of server names.
  - `mcp.excluded`: Blocklist of server names.
- **Server Properties (`mcpServers.<name>`):**
  - `command`: Stdio executable.
  - `url`/`httpUrl`: SSE or HTTP streaming endpoints.
  - `args`: CLI arguments.
  - `env`: Environment variables (supports recursive expansion like `$VAR` or `%VAR%`).
  - `trust`: If `true`, bypasses tool call confirmation prompts.
  - `includeTools` / `excludeTools`: Filter available tools.

### Security & Sanitization
- **Automatic Redaction:** Sensitive variables (matching `*TOKEN*`, `*SECRET*`, `*KEY*`, etc.) are redacted from the base process environment.
- **Explicit Overrides:** Variables explicitly defined in the `env` block of `settings.json` are **trusted** and exempt from redaction.
- **Sandboxing:** Ensure MCP executables are accessible if sandboxing is enabled.

### Rich Content & Prompts
- **Rich Content:** Tools can return mixed parts (text, images, audio) using the standard MCP `ContentBlock` array.
- **Prompts as Commands:** Servers can register prompts that the CLI exposes as slash commands (e.g., `/my-prompt`).

### Troubleshooting Commands
- `/mcp`: List connected servers and available tools.
- `/mcp auth`: Manage OAuth authentication for remote servers.
## 7. Model Routing & Fallback Policies

Gemini CLI includes a model routing feature that automatically switches to a fallback model in case of a model failure (e.g., quota or server errors).

### Routing Mechanism
- **ModelAvailabilityService:** Monitors health and routes requests based on availability policies.
- **User Consent:** The CLI prompts for approval before switching models for interactive tasks.
- **Silent Fallback:** Internal utilities (completion/classification) use a silent chain: `gemini-2.5-flash-lite` → `gemini-2.5-flash` → `gemini-2.5-pro`.

### Model Selection Precedence
The CLI determines the active model based on this priority:
1. `--model` command-line flag.
2. `GEMINI_MODEL` environment variable.
3. `model.name` in `settings.json`.
## 8. Model Selection & Best Practices

The `/model` command (or the `--model` flag) allows you to configure the Gemini model used for the CLI session.

### Model Options
- **Auto (Recommended):** The system dynamically selects between Pro and Flash models based on task complexity.
- **Manual:** Select a specific model (e.g., `gemini-2.5-pro` for deep reasoning, `gemini-2.5-flash` for speed).

### Best Practices
- **Default to Auto:** Optimal for most workflows, balancing latency and reasoning capabilities.
- **Explicit Pro:** Use for complex, multi-stage debugging or architectural scaffolding.
- **Explicit Flash/Flash-Lite:** Use for simple tasks like formatting, translation, or quick summaries.

## 9. Development Workflows

Standard procedures for maintaining the AxQxOS environment.

### Web Dashboard
- **Start Dev Server**: Run `pnpm dev` in the root or `npm run dev` in `apps/web`. The dashboard is hosted on port `5173`.
- **Build Production**: Run `pnpm build --filter @world-os/web`.

### Pam Orchestrator & Self-Healing
- **Logic Location**: `apps/web/src/lib/pam.ts` handles drift analysis and ledger sealing.
- **Simulation**: Use the `/governance` dashboard to inject telemetry and trigger `AUTO_FIX` events.
- **Policy Configuration**: `agents/pam_orchestrator.json` defines auto-fix thresholds and forbidden geometry guardrails.

### Audit & Validation
- **Fossil Ingestion**: Use `scripts/ingest_fossil.py` (if available) or manual mapping for sim-to-real validation.
- **Reporting**: Finalize `audit_report.md` after every major training run or architecture merge.

> **Note:** These settings apply to the primary CLI session and do not override models specifically configured for sub-agents.
