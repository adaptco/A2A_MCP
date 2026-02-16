export const diffRules = (oldRules: string[], newRules: string[]): string[] => {
  return newRules.filter((rule) => !oldRules.includes(rule));
};
