
import { onFlow } from 'genkitx-firebase/functions';
import * as logger from 'firebase-functions/logger';
import { defineFlow, run } from 'genkit';
import { vertexAI } from 'genkitx-vertexai';
import { writeToFile } from './agent';
import { z } from 'genkit';

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
        tools: [writeToFile],
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
