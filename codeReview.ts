
import { defineFlow } from 'genkit';
import { vertexAI } from 'genkitx-vertexai';
import { z } from 'zod';

// Define the code review flow
export const codeReviewFlow = defineFlow(
  {
    name: 'codeReviewFlow',
    inputSchema: z.string(),
    outputSchema: z.string(),
  },
  async (code) => {
    const llm = vertexAI.model('gemini-1.5-flash-preview');

    const prompt = `
      As a senior software engineer, please review the following code.
      Focus on identifying potential issues that could arise after deployment, such as:
      - Performance bottlenecks
      - Security vulnerabilities
      - Unhandled edge cases
      - Scalability problems

      Provide a detailed analysis and suggestions for improvement.

      Code:
      '''
      ${code}
      '''
    `;

    const response = await llm.generate({
      prompt,
      config: {
        temperature: 0.2,
      },
    });

    return response.text();
  }
);
