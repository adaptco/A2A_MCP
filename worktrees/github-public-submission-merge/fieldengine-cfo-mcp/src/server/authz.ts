export const isAuthorized = (role: string, action: string): boolean => {
  return role.length > 0 && action.length > 0;
};
