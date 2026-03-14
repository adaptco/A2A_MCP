
import { writeFile } from 'fs/promises';
import { z } from 'genkit';
import { defineTool } from 'genkit/tool';

// Define the tool for writing to a file
export const writeToFile = defineTool(
  {
    name: 'writeToFile',
    description: 'Writes content to a file. This tool is used to generate software artifacts, such as code files, documentation, or configuration files.',
    inputSchema: z.object({
      path: z.string().describe('The path of the file to be written. This should be a relative path from the project root.'),
      content: z.string().describe('The content to write to the file.'),
    }),
    outputSchema: z.string(),
  },
  async ({ path, content }) => {
    await writeFile(path, content);
    return `Successfully wrote to ${path}`;
  }
);
