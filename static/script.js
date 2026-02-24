
document.addEventListener("DOMContentLoaded", () => {
    const createBtn = document.getElementById("create-agent-btn");
    const adaptBtn = document.getElementById("adapt-agent-btn");
    const agentDisplay = document.getElementById("agent-display");
    const agentJson = document.getElementById("agent-json");
    const logList = document.getElementById("log-list");

    let currentArtifactId = null;
    let pollInterval = null;

    const log = (message) => {
        const li = document.createElement("li");
        li.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
        logList.prepend(li);
    };

    const updateAgentDisplay = (agent) => {
        agentDisplay.classList.remove("hidden");
        agentJson.textContent = JSON.stringify(agent, null, 2);
    };

    const pollAgentStatus = async () => {
        if (!currentArtifactId) return;

        try {
            const response = await fetch(`/agents/${currentArtifactId}`);
            if (!response.ok) throw new Error("Failed to fetch agent status.");
            
            const agent = await response.json();
            updateAgentDisplay(agent);

            log(`Agent state is now: ${agent.state}`);

            if (agent.state === "TRAINED" || agent.state === "FAILED") {
                clearInterval(pollInterval);
                pollInterval = null;
                log("Polling stopped. Final state reached.");
                createBtn.disabled = false; // Allow creating a new agent
            }
        } catch (error) {
            log(`Error polling: ${error.message}`);
            clearInterval(pollInterval);
        }
    };

    createBtn.addEventListener("click", async () => {
        log("Creating a new agent...");
        createBtn.disabled = true;
        adaptBtn.disabled = true;

        try {
            const response = await fetch("/agents", { method: "POST" });
            if (!response.ok) throw new Error("Failed to create agent.");
            
            const agent = await response.json();
            currentArtifactId = agent.artifact_id;
            
            log(`Agent created successfully! Artifact ID: ${currentArtifactId}`);
            updateAgentDisplay(agent);

            adaptBtn.disabled = false;

        } catch (error) {
            log(`Error: ${error.message}`);
            createBtn.disabled = false;
        }
    });

    adaptBtn.addEventListener("click", async () => {
        if (!currentArtifactId) {
            log("No agent selected to adapt.");
            return;
        }

        log("Starting LoRA adaptation process...");
        adaptBtn.disabled = true;

        try {
            const response = await fetch(`/agents/${currentArtifactId}/adapt`, { method: "POST" });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || "Failed to start adaptation.");
            }

            log("Adaptation process initiated. Polling for status updates...");
            if (pollInterval) clearInterval(pollInterval);
            pollInterval = setInterval(pollAgentStatus, 2000);

        } catch (error) {
            log(`Error: ${error.message}`);
            adaptBtn.disabled = false;
        }
    });
});
