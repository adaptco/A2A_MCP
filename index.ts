import { configureGenkit } from 'genkit';
import { onFlow } from 'genkitx-firebase/functions';
import * as logger from 'firebase-functions/logger';
import { defineFlow, run } from 'genkit';
import { vertexAI } from 'genkitx-vertexai';
import { writeToFile } from './agent';
import { codeReviewFlow } from './codeReview';
import { deploymentMonitorFlow } from './deploymentMonitor'; // Import the new deployment monitor flow
import { z } from 'zod';

// Initialize Genkit with the Vertex AI plugin
configureGenkit({
  plugins: [
    vertexAI(),
  ],
  logLevel: 'debug',
  enableTracingAndMetrics: true,
});

// Define the agent flow
const agentFlow = defineFlow(
  {
    name: 'agentFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (prompt) => {
    const llm = vertexAI.model('gemini-1.5-flash-preview');

    const response = await run('call-agent', async () =>
      llm.generate({
        prompt,
        tools: [writeToFile, codeReviewFlow, deploymentMonitorFlow], // Add the deployment monitor flow to the tools
        config: {
          temperature: 0.2,
        },
      })
    );

    const toolRequest = response.toolRequest();
    if (toolRequest) {
      const toolResponse = await run('run-tool', () =>
        toolRequest.run()
      );
      return toolResponse.output as string;
    }

    return response.text();
  }
);

export const agent = onFlow(
  {
    name: 'agent',
    ...agentFlow,
  },
  async (input) => {
    logger.info('Agent flow invoked with input:', input);
    return await agentFlow.run(input);
  }
);

// Export the code review flow
export const codeReview = onFlow(
  {
    name: 'codeReview',
    ...codeReviewFlow,
  },
  async (input) => {
    logger.info('Code review flow invoked with input:', input);
    return await codeReviewFlow.run(input);
  }
);

// Export the deployment monitor flow
export const deploymentMonitor = onFlow(
  {
    name: 'deploymentMonitor',
    ...deploymentMonitorFlow,
  },
  async (input) => {
    logger.info('Deployment monitor flow invoked with input:', input);
    return await deploymentMonitorFlow.run(input);
  }
);