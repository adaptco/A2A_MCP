export const overrideSchemaResource = {
  uri: 'schema://override',
  read: async () => ({ type: 'object' })
};
