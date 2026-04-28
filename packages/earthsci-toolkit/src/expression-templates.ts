/**
 * Parse-time expansion of `expression_templates` (RFC v2 §4 Option A,
 * docs/content/rfcs/ast-expression-templates.md, esm-giy).
 *
 * - Templates are component-local: declared inside one Model or
 *   ReactionSystem; visible only inside that component.
 * - Round-trip is always-expanded: the `expression_templates` block is
 *   removed and `apply_expression_template` op-nodes are replaced with
 *   the substituted body before downstream parsing/canonicalization.
 * - Pure syntactic substitution; no recursion; templates may not call
 *   templates.
 */

/** Local copy of the schema validation error so we don't introduce a
 * circular import with parse.ts. The runtime check is `instanceof
 * Error` plus `.name === 'SchemaValidationError'` in callers. */
export class TemplateExpansionError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'SchemaValidationError'
  }
}

const APPLY_OP = 'apply_expression_template'

function deepClone<T>(v: T): T {
  return JSON.parse(JSON.stringify(v)) as T
}

function isObj(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

function scanForApplyTemplate(node: unknown): boolean {
  if (Array.isArray(node)) {
    return node.some(scanForApplyTemplate)
  }
  if (isObj(node)) {
    if (node.op === APPLY_OP) return true
    for (const v of Object.values(node)) {
      if (scanForApplyTemplate(v)) return true
    }
  }
  return false
}

function parseEsmVersion(v: unknown): [number, number, number] | null {
  if (typeof v !== 'string') return null
  const m = /^(\d+)\.(\d+)\.(\d+)$/.exec(v)
  if (!m) return null
  return [Number(m[1]), Number(m[2]), Number(m[3])]
}

function versionAtLeast(
  v: [number, number, number],
  target: [number, number, number],
): boolean {
  for (let i = 0; i < 3; i++) {
    if (v[i] > target[i]) return true
    if (v[i] < target[i]) return false
  }
  return true
}

/** Substitute `bindings` into a template `body` Expression. Walks
 * Expression-positioned fields only (args / expr / values) so a parameter
 * that happens to coincide with an op name does not collide. */
function substituteBody(
  body: unknown,
  bindings: Record<string, unknown>,
): unknown {
  if (typeof body === 'string') {
    if (Object.prototype.hasOwnProperty.call(bindings, body)) {
      return deepClone(bindings[body])
    }
    return body
  }
  if (Array.isArray(body)) {
    return body.map((b) => substituteBody(b, bindings))
  }
  if (isObj(body)) {
    const out: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(body)) {
      if (k === 'args' || k === 'values') {
        out[k] = Array.isArray(v) ? v.map((x) => substituteBody(x, bindings)) : v
      } else if (k === 'expr') {
        out[k] = substituteBody(v, bindings)
      } else {
        out[k] = v
      }
    }
    return out
  }
  return body
}

function expandApplyNode(
  node: Record<string, unknown>,
  templates: Record<string, Record<string, unknown>>,
): unknown {
  const name = node.name
  if (typeof name !== 'string' || !(name in templates)) {
    throw new TemplateExpansionError(
      `apply_expression_template references unknown template '${String(name)}'`)
  }
  const template = templates[name]
  const params = Array.isArray(template.params) ? (template.params as string[]) : []
  const bindingsRaw = node.bindings
  if (!isObj(bindingsRaw)) {
    throw new TemplateExpansionError(`apply_expression_template '${name}' missing 'bindings' object`)
  }
  const bindings = bindingsRaw as Record<string, unknown>
  const missing = params.filter((p) => !(p in bindings))
  if (missing.length > 0) {
    throw new TemplateExpansionError(
      `apply_expression_template '${name}' missing bindings: ${JSON.stringify(missing)}`)
  }
  const extras = Object.keys(bindings).filter((k) => !params.includes(k))
  if (extras.length > 0) {
    throw new TemplateExpansionError(
      `apply_expression_template '${name}' has unknown bindings: ${JSON.stringify(extras)}`)
  }
  return substituteBody(deepClone(template.body), bindings)
}

function expandWalk(
  node: unknown,
  templates: Record<string, Record<string, unknown>>,
): unknown {
  if (Array.isArray(node)) {
    return node.map((v) => expandWalk(v, templates))
  }
  if (isObj(node)) {
    if (node.op === APPLY_OP) {
      return expandApplyNode(node, templates)
    }
    const out: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(node)) {
      out[k] = expandWalk(v, templates)
    }
    return out
  }
  return node
}

function expandInComponent(component: Record<string, unknown>): void {
  const tmpls = component.expression_templates
  delete component.expression_templates
  if (isObj(tmpls) && Object.keys(tmpls).length > 0) {
    const templates = tmpls as Record<string, Record<string, unknown>>
    for (const key of Object.keys(component)) {
      if (key === 'subsystems') continue
      component[key] = expandWalk(component[key], templates)
    }
  }
  const subs = component.subsystems
  if (isObj(subs)) {
    for (const sub of Object.values(subs)) {
      if (isObj(sub) && !('ref' in sub)) {
        expandInComponent(sub as Record<string, unknown>)
      }
    }
  }
}

/**
 * Expand `expression_templates` in place across all models and reaction
 * systems. Mutates `data`. Throws SchemaValidationError if the file
 * declares esm < 0.4.0 but uses templates or apply_expression_template.
 */
export function expandExpressionTemplates(data: unknown): void {
  if (!isObj(data)) return
  const root = data as Record<string, unknown>

  let hasBlock = false
  for (const section of ['models', 'reaction_systems']) {
    const components = root[section]
    if (!isObj(components)) continue
    for (const comp of Object.values(components)) {
      if (isObj(comp) && comp.expression_templates) {
        hasBlock = true
        break
      }
    }
    if (hasBlock) break
  }
  const hasUse = scanForApplyTemplate(data)

  if (hasUse || hasBlock) {
    const v = parseEsmVersion(root.esm)
    if (v === null || !versionAtLeast(v, [0, 4, 0])) {
      throw new TemplateExpansionError(
        `expression_templates / apply_expression_template require esm: 0.4.0 or later (file declares esm: '${String(root.esm)}')`)
    }
  }

  for (const section of ['models', 'reaction_systems']) {
    const components = root[section]
    if (!isObj(components)) continue
    for (const comp of Object.values(components)) {
      if (isObj(comp)) expandInComponent(comp as Record<string, unknown>)
    }
  }
}
