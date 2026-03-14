/**
 * VH2 MCP — Schema Layer
 *
 * Implements the same API surface as zod for MCP tool/resource schemas,
 * but with zero external dependencies. Uses the passthrough strategy:
 *   - Stub tools: z.object({}).passthrough() → accepts any params
 *   - Live tools: z.object({ field: z.number() }) → validates + coerces
 *
 * Usage mirrors zod exactly so a future swap to the real zod package
 * requires only changing this import, nothing else.
 */

class ZodType {
  constructor(type, config = {}) {
    this._type   = type
    this._config = config
    this._optional = false
    this._description = null
  }

  optional()            { this._optional = true; return this }
  describe(d)           { this._description = d; return this }

  /** Validate + coerce a value, returns { success, data, error } */
  safeParse(value) {
    try {
      return { success: true, data: this._coerce(value) }
    } catch (e) {
      return { success: false, error: e.message }
    }
  }

  parse(value) {
    const r = this.safeParse(value)
    if (!r.success) throw new Error(`Schema validation failed: ${r.error}`)
    return r.data
  }

  _coerce(value) { return value }  // base: passthrough

  /** JSON Schema representation for MCP tool registration */
  toJsonSchema() { return { type: this._type } }
}

class ZodNumber extends ZodType {
  constructor(cfg) { super('number', cfg) }
  min(n) { this._config.min = n; return this }
  max(n) { this._config.max = n; return this }
  _coerce(v) {
    const n = Number(v)
    if (isNaN(n)) throw new Error(`Expected number, got ${typeof v}`)
    if (this._config.min !== undefined && n < this._config.min)
      throw new Error(`Value ${n} < min ${this._config.min}`)
    if (this._config.max !== undefined && n > this._config.max)
      throw new Error(`Value ${n} > max ${this._config.max}`)
    return n
  }
  toJsonSchema() {
    const s = { type: 'number' }
    if (this._config.min !== undefined) s.minimum = this._config.min
    if (this._config.max !== undefined) s.maximum = this._config.max
    if (this._description)              s.description = this._description
    return s
  }
}

class ZodString extends ZodType {
  constructor(cfg) { super('string', cfg) }
  _coerce(v) {
    if (typeof v !== 'string') throw new Error(`Expected string, got ${typeof v}`)
    return v
  }
  toJsonSchema() {
    const s = { type: 'string' }
    if (this._description) s.description = this._description
    return s
  }
}

class ZodBoolean extends ZodType {
  constructor(cfg) { super('boolean', cfg) }
  _coerce(v) { return Boolean(v) }
  toJsonSchema() { return { type: 'boolean' } }
}

class ZodEnum extends ZodType {
  constructor(values) { super('string'); this._values = values }
  _coerce(v) {
    if (!this._values.includes(v))
      throw new Error(`Expected one of [${this._values.join(', ')}], got "${v}"`)
    return v
  }
  toJsonSchema() { return { type: 'string', enum: this._values } }
}

class ZodObject extends ZodType {
  constructor(shape, passthrough = false) {
    super('object')
    this._shape       = shape       // { key: ZodType }
    this._passthrough = passthrough // accept unknown keys
  }

  passthrough() { this._passthrough = true; return this }

  _coerce(value) {
    if (typeof value !== 'object' || value === null)
      throw new Error(`Expected object, got ${typeof value}`)

    if (this._passthrough) {
      // Validate known fields, pass unknown through
      const result = { ...value }
      for (const [key, schema] of Object.entries(this._shape)) {
        if (key in value) {
          result[key] = schema.parse(value[key])
        } else if (!schema._optional) {
          throw new Error(`Missing required field: ${key}`)
        }
      }
      return result
    }

    // Strict: only known fields
    const result = {}
    for (const [key, schema] of Object.entries(this._shape)) {
      if (key in value) {
        result[key] = schema.parse(value[key])
      } else if (!schema._optional) {
        throw new Error(`Missing required field: ${key}`)
      }
    }
    return result
  }

  /** JSON Schema for MCP inputSchema */
  toJsonSchema() {
    const properties = {}
    const required   = []
    for (const [key, schema] of Object.entries(this._shape)) {
      properties[key] = schema.toJsonSchema()
      if (this._description) properties[key].description = schema._description
      if (!schema._optional) required.push(key)
    }
    const s = { type: 'object', properties }
    if (required.length) s.required = required
    if (this._passthrough) s.additionalProperties = true
    return s
  }
}

// ── Public z.* API ──────────────────────────────────────────────────────────
export const z = {
  object:  (shape = {}) => new ZodObject(shape),
  number:  ()           => new ZodNumber({}),
  string:  ()           => new ZodString({}),
  boolean: ()           => new ZodBoolean({}),
  enum:    (values)     => new ZodEnum(values),
}
