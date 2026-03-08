export interface RuleDiffSummary {
  added: string[];
  removed: string[];
  unchanged: string[];
}

const unique = (rules: string[]): string[] => Array.from(new Set(rules));

export const compareRules = (oldRules: string[], newRules: string[]): RuleDiffSummary => {
  const previous = unique(oldRules);
  const current = unique(newRules);

  return {
    added: current.filter((rule) => !previous.includes(rule)),
    removed: previous.filter((rule) => !current.includes(rule)),
    unchanged: current.filter((rule) => previous.includes(rule)),
  };
};

export const diffRules = (oldRules: string[], newRules: string[]): string[] => {
  return compareRules(oldRules, newRules).added;
};
