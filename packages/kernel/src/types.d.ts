declare module "stable-stringify" {
  function stringify(value: unknown, replacer?: unknown, space?: number | string): string;
  export = stringify;
}

declare module "lodash.clonedeep" {
  function cloneDeep<T>(value: T): T;
  export = cloneDeep;
}
