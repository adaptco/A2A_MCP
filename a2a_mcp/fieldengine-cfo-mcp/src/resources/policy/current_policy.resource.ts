export const currentPolicyResource = {
  uri: 'policy://current',
  read: async () => ({ version: '0.1.0', diffs: [] as string[] })
};
