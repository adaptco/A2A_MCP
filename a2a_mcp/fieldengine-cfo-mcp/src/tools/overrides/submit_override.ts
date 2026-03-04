export const submit_override = async (input: Record<string, unknown>): Promise<Record<string, unknown>> => ({
  tool: 'submit_override',
  input,
  status: 'stubbed'
});
