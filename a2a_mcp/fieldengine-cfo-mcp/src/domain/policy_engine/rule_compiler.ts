export const compileRules = (policy: Record<string, unknown>): Array<string> => {
  return Object.keys(policy);
};
