# A2A-MCP-Orchestrator
### Multi-Agent Model Context Protocol (MCP) Orchestration Hub

**A2A-MCP-Orchestrator** is a high-performance orchestration layer designed for **Agent-to-Agent (A2A)** communication. 

## 🛰 Architecture
```mermaid
graph TD
    User((User)) --> Hub[Orchestration Hub]
    Hub -->|Task| A1[Researcher]
    A1 -->|Artifact| Hub
    Hub -->|Context| A2[Coder]
    A2 -->|Solution| Hub
📋 Standardized Artifact Schema
class MCPArtifact(BaseModel):
    artifact_id: str
    type: str  # research_doc, code_solution
    content: str
🚀 Getting Started
docker build -t a2a-hub . && docker run -p 8000:8000 a2a-hub
---

### 🛠️ Step 2: Infrastructure as Code (The Agentic "Folder" Trick)
Now we will create the Kubernetes directory and manifest in one move.

1.  **Action**: Click the **[+] (Add file)** button near the top right of your [repository file list](https://github.com/adaptco-main/A2A_MCP) and select **"Create new file"**.
2.  **Name the file**: Type exactly `k8s/deployment.yaml`. (Typing the `/` automatically creates the folder).
3.  **Payload**: Paste this configuration:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: a2a-mcp-orchestrator
spec:
  replicas: 3
  selector:
    matchLabels:
      app: mcp-hub
  template:
    metadata:
      labels:
        app: mcp-hub
    spec:
      containers:
      - name: orchestrator
        image: a2a-hub:latest
        ports:
        - containerPort: 8000
