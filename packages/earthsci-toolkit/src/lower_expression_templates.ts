/**
 * Load-time expansion pass for `apply_expression_template` ops
 * (esm-spec §9.6 / docs/rfcs/ast-expression-templates.md).
 *
 * Walks each `models.<m>` and `reaction_systems.<rs>` block; if an
 * `expression_templates` entry is present, every `apply_expression_template`
 * node anywhere in that component's expressions is replaced by the
 * substituted template body. After the pass, the component carries no
 * `expression_templates` block and no `apply_expression_template` ops —
 * downstream consumers see only normal Expression ASTs.
 *
 * Operates on the pre-coercion JSON view (plain objects) — runs in
 * `load()` after schema validation but before typed coercion.
 *
 * Errors:
 *   - apply_expression_template_unknown_template
 *   - apply_expression_template_bindings_mismatch
 *   - apply_expression_template_recursive_body
 *   - apply_expression_template_version_too_old
 */

import { isNumericLiteral } from './numeric-literal.js'

const APPLY_OP = 'apply_expression_template'

export class ExpressionTemplateError extends Error {
  constructor(public code: string, message: string) {
    super(`[${code}] ${message}`)
    this.name = 'ExpressionTemplateError'
  }
}

type Json = unknown
type Templates = Record<string, { params: string[]; body: Json }>

function isObject(v: unknown): v is Record<string, unknown> {
  return (
    typeof v === 'object' && v !== null && !Array.isArray(v) && !isNumericLiteral(v)
  )
}

function deepClone<T>(v: T): T {
  if (v === null || v === undefined) return v
  if (isNumericLiteral(v)) return v // preserve symbol-tagged literals as-is
  if (Array.isArray(v)) return v.map(deepClone) as unknown as T
  if (typeof v === 'object') {
    const out: Record<string, unknown> = {}
    for (const k of Object.keys(v as object)) out[k] = deepClone((v as Record<string, unknown>)[k])
    return out as unknown as T
  }
  return v
}

/** Substitute parameter occurrences in a template body. */
function substitute(body: Json, bindings: Record<string, Json>): Json {
  if (typeof body === 'string') {
    if (Object.prototype.hasOwnProperty.call(bindings, body)) {
      return deepClone(bindings[body])
    }
    return body
  }
  if (Array.isArray(body)) {
    return body.map((c) => substitute(c, bindings))
  }
  if (isObject(body)) {
    const out: Record<string, unknown> = {}
    for (const k of Object.keys(body)) {
      out[k] = substitute(body[k], bindings)
    }
    return out
  }
  return body
}

/** Validate a template body contains no apply_expression_template nodes. */
function assertNoNestedApply(body: Json, templateName: string, path: string): void {
  if (Array.isArray(body)) {
    for (let i = 0; i < body.length; i++) {
      assertNoNestedApply(body[i], templateName, `${path}/${i}`)
    }
    return
  }
  if (isObject(body)) {
    if (body.op === APPLY_OP) {
      throw new ExpressionTemplateError(
        'apply_expression_template_recursive_body',
        `expression_templates.${templateName}: body contains nested 'apply_expression_template' at ${path}; templates MUST NOT call other templates`,
      )
    }
    for (const k of Object.keys(body)) {
      assertNoNestedApply(body[k], templateName, `${path}/${k}`)
    }
  }
}

function validateTemplates(templates: Templates, scope: string): void {
  for (const [name, decl] of Object.entries(templates)) {
    if (!decl || typeof decl !== 'object') {
      throw new ExpressionTemplateError(
        'apply_expression_template_invalid_declaration',
        `${scope}.expression_templates.${name}: entry must be an object with params + body`,
      )
    }
    const params = (decl as { params?: unknown }).params
    if (!Array.isArray(params) || params.length === 0) {
      throw new ExpressionTemplateError(
        'apply_expression_template_invalid_declaration',
        `${scope}.expression_templates.${name}: 'params' must be a non-empty array of strings`,
      )
    }
    const seen = new Set<string>()
    for (const p of params) {
      if (typeof p !== 'string' || p.length === 0) {
        throw new ExpressionTemplateError(
          'apply_expression_template_invalid_declaration',
          `${scope}.expression_templates.${name}: param names must be non-empty strings`,
        )
      }
      if (seen.has(p)) {
        throw new ExpressionTemplateError(
          'apply_expression_template_invalid_declaration',
          `${scope}.expression_templates.${name}: param '${p}' is declared twice`,
        )
      }
      seen.add(p)
    }
    if (!('body' in (decl as object))) {
      throw new ExpressionTemplateError(
        'apply_expression_template_invalid_declaration',
        `${scope}.expression_templates.${name}: 'body' is required`,
      )
    }
    assertNoNestedApply((decl as { body: Json }).body, name, '/body')
  }
}

function expandApply(node: Record<string, unknown>, templates: Templates, scope: string): Json {
  const name = node.name
  if (typeof name !== 'string' || name.length === 0) {
    throw new ExpressionTemplateError(
      'apply_expression_template_invalid_declaration',
      `${scope}: apply_expression_template node missing or empty 'name'`,
    )
  }
  const decl = templates[name]
  if (!decl) {
    throw new ExpressionTemplateError(
      'apply_expression_template_unknown_template',
      `${scope}: apply_expression_template references undeclared template '${name}'`,
    )
  }
  const bindings = node.bindings
  if (!isObject(bindings)) {
    throw new ExpressionTemplateError(
      'apply_expression_template_bindings_mismatch',
      `${scope}: apply_expression_template '${name}' missing 'bindings' object`,
    )
  }
  const provided = new Set(Object.keys(bindings))
  const declared = new Set(decl.params)
  for (const p of decl.params) {
    if (!provided.has(p)) {
      throw new ExpressionTemplateError(
        'apply_expression_template_bindings_mismatch',
        `${scope}: apply_expression_template '${name}' missing binding for param '${p}'`,
      )
    }
  }
  for (const p of provided) {
    if (!declared.has(p)) {
      throw new ExpressionTemplateError(
        'apply_expression_template_bindings_mismatch',
        `${scope}: apply_expression_template '${name}' supplies unknown param '${p}'`,
      )
    }
  }
  // Recursively expand any apply_expression_template nodes inside the
  // bindings (templates can take other-template results as args even if
  // they cannot themselves call templates internally).
  const resolvedBindings: Record<string, Json> = {}
  for (const [k, v] of Object.entries(bindings)) {
    resolvedBindings[k] = walk(v, templates, scope)
  }
  return substitute(decl.body, resolvedBindings)
}

function walk(node: Json, templates: Templates, scope: string): Json {
  if (Array.isArray(node)) {
    return node.map((c) => walk(c, templates, scope))
  }
  if (isObject(node)) {
    if (node.op === APPLY_OP) {
      return expandApply(node, templates, scope)
    }
    const out: Record<string, unknown> = {}
    for (const k of Object.keys(node)) {
      out[k] = walk(node[k], templates, scope)
    }
    return out
  }
  return node
}

/** Walk the file looking for apply_expression_template ops anywhere. */
function findStrayApplyOps(view: unknown): string[] {
  const hits: string[] = []
  const visit = (v: unknown, path: string): void => {
    if (Array.isArray(v)) {
      for (let i = 0; i < v.length; i++) visit(v[i], `${path}/${i}`)
      return
    }
    if (isObject(v)) {
      if (v.op === APPLY_OP) hits.push(path)
      for (const k of Object.keys(v)) visit(v[k], `${path}/${k}`)
    }
  }
  visit(view, '')
  return hits
}

function parseSemver(v: unknown): { major: number; minor: number; patch: number } | null {
  if (typeof v !== 'string') return null
  const m = /^(\d+)\.(\d+)\.(\d+)$/.exec(v)
  if (!m) return null
  return { major: Number(m[1]), minor: Number(m[2]), patch: Number(m[3]) }
}

/**
 * Reject `apply_expression_template` and `expression_templates` in files
 * declaring `esm` < 0.4.0. Operates on the pre-coercion JSON view.
 */
export function rejectExpressionTemplatesPreV04(view: unknown): void {
  if (!isObject(view)) return
  const v = parseSemver((view as { esm?: unknown }).esm)
  if (!v) return
  const isPreV04 = v.major === 0 && v.minor < 4
  if (!isPreV04) return

  const offences: string[] = []
  // expression_templates blocks anywhere
  const root = view as Record<string, unknown>
  for (const compKind of ['models', 'reaction_systems'] as const) {
    const comps = root[compKind]
    if (!isObject(comps)) continue
    for (const [name, comp] of Object.entries(comps)) {
      if (isObject(comp) && 'expression_templates' in comp) {
        offences.push(`/${compKind}/${name}/expression_templates`)
      }
    }
  }
  // apply_expression_template ops anywhere in the AST
  for (const path of findStrayApplyOps(view)) offences.push(path)

  if (offences.length > 0) {
    throw new ExpressionTemplateError(
      'apply_expression_template_version_too_old',
      `expression_templates / apply_expression_template require esm >= 0.4.0; file declares ${(view as { esm?: string }).esm}. Offending paths: ${offences.join(', ')}`,
    )
  }
}

interface Component {
  expression_templates?: unknown
  [k: string]: unknown
}

/**
 * Expand all apply_expression_template nodes in the given file (in place
 * is OK — we mutate a clone). Returns a new file object with templates
 * expanded and `expression_templates` blocks removed.
 *
 * Pre-condition: the input has been schema-validated.
 */
export function lowerExpressionTemplates<T extends object>(file: T): T {
  rejectExpressionTemplatesPreV04(file)

  if (!isObject(file)) return file
  const root = file as Record<string, unknown>

  // First, scan globally for any apply_expression_template — used to
  // detect orphan ops in components that have no templates block.
  const globalOps = findStrayApplyOps(file)
  if (globalOps.length === 0) {
    // No apply ops anywhere; just strip empty expression_templates blocks
    // for canonical-form invariance and return.
    return stripExpressionTemplates(file)
  }

  // Walk both components families.
  const out = deepClone(root)
  for (const compKind of ['models', 'reaction_systems'] as const) {
    const comps = out[compKind]
    if (!isObject(comps)) continue
    for (const [compName, compRaw] of Object.entries(comps)) {
      if (!isObject(compRaw)) continue
      const comp = compRaw as Component
      const tplRaw = comp.expression_templates
      const templates: Templates = {}
      if (isObject(tplRaw)) {
        for (const [tname, tdecl] of Object.entries(tplRaw)) {
          templates[tname] = tdecl as Templates[string]
        }
        validateTemplates(templates, `${compKind}.${compName}`)
      }
      // Walk every property except expression_templates (we don't
      // expand inside template bodies — those are validated above).
      for (const k of Object.keys(comp)) {
        if (k === 'expression_templates') continue
        comp[k] = walk(comp[k], templates, `${compKind}.${compName}.${k}`)
      }
      delete comp.expression_templates
    }
  }

  // After expansion, there must be no apply_expression_template ops left
  // anywhere in the file.
  const leftover = findStrayApplyOps(out)
  if (leftover.length > 0) {
    throw new ExpressionTemplateError(
      'apply_expression_template_unknown_template',
      `apply_expression_template ops remain after expansion at: ${leftover.join(', ')} — likely referenced from a component lacking an expression_templates block`,
    )
  }

  return out as T
}

function stripExpressionTemplates<T extends object>(file: T): T {
  if (!isObject(file)) return file
  const out = deepClone(file as Record<string, unknown>)
  for (const compKind of ['models', 'reaction_systems'] as const) {
    const comps = out[compKind]
    if (!isObject(comps)) continue
    for (const compRaw of Object.values(comps)) {
      if (isObject(compRaw) && 'expression_templates' in compRaw) {
        delete (compRaw as Record<string, unknown>).expression_templates
      }
    }
  }
  return out as T
}
