if (typeof fetch !== "function") {
  throw new Error("This example requires a runtime with the Fetch API (Node.js 18+).");
}

// Replace the placeholder values below before running.
fetch("https://api.github.com/repos/your-org/your-repo/dispatches", {
  method: "POST",
  headers: {
    Authorization: "Bearer YOUR_TOKEN",
    Accept: "application/vnd.github.v3+json",
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    event_type: "freeze_artifact",
    client_payload: {
      artifact_id: "abc123",
    },
  }),
})
  .then((response) => {
    if (!response.ok) {
      return response.text().then((body) => {
        throw new Error(
          `GitHub API request failed with ${response.status} ${response.statusText}: ${body}`
        );
      });
    }

    console.log("Dispatch event queued.");
  })
  .catch((error) => {
    console.error("Dispatch failed:", error.message);
    process.exitCode = 1;
  });
