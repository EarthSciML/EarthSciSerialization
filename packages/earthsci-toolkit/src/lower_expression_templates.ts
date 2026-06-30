/**
 * Load-time rewrite pass for `expression_templates` (esm-spec §9.6 /
 * docs/rfcs/ast-expression-templates.md).
 *
 * An `expression_templates` entry is a **rewrite rule** with `params`
 * (metavariables), a `body` (the replacement Expression), and an optional
 * `match` pattern. This single engine covers both application modes:
 *
 *   - **No `match`** — the entry is applied only by an explicit
 *     `apply_expression_template` node that names it and supplies
 *     per-parameter `bindings` (the original template-expansion path).
 *   - **With `match`** — the entry is an *auto-applied* rewrite rule.
 *     `match` is a pattern Expression in which the params are wildcards:
 *     a param in an operand/`args` position binds to the matched sub-AST;
 *     a param in a scalar field (e.g. `dim`, `side`) binds to the matched
 *     literal. The rule fires wherever the pattern structurally matches.
 *
 * Rewriting is a **single bottom-up pass** per expression tree, applying
 * `match` rules in template **declaration order**; a replacement `body` is
 * **not** re-scanned for further matches. A `match` rule whose `body`
 * re-introduces its own pattern is rejected with diagnostic
 * `rewrite_rule_nonterminating`.
 *
 * Walks each `models.<m>` and `reaction_systems.<rs>` block, rewriting
 * every expression position in the component. After the pass the component
 * carries no `expression_templates` block and no `apply_expression_template`
 * ops — downstream consumers see only normal Expression ASTs.
 *
 * Operates on the pre-coercion JSON view (plain objects) — runs in
 * `load()` after schema validation but before typed coercion.
 *
 * Errors:
 *   - apply_expression_template_unknown_template
 *   - apply_expression_template_bindings_mismatch
 *   - apply_expression_template_recursive_body
 *   - apply_expression_template_version_too_old
 *   - apply_expression_template_invalid_declaration
 *   - rewrite_rule_nonterminating
 */

import { isNumericLiteral, numericValue } from './numeric-literal.js'

const APPLY_OP = 'apply_expression_template'

export class ExpressionTemplateError extends Error {
  constructor(public code: string, message: string) {
    super(`[${code}] ${message}`)
    this.name = 'ExpressionTemplateError'
  }
}

type Json = unknown
type TemplateDecl = { params: string[]; body: Json; match?: Json }
/** Named templates invoked explicitly via `apply_expression_template` (no `match`). */
type Templates = Record<string, TemplateDecl>

/** An auto-applied rewrite rule (a template carrying a `match` pattern). */
interface MatchRule {
  name: string
  params: Set<string>
  match: Json
  body: Json
}

function isObject(v: unknown): v is Record<string, unknown> {
  return (
    typeof v === 'object' && v !== null && !Array.isArray(v) && !isNumericLiteral(v)
  )
}

/**
 * Structural deep equality over the JSON AST, treating plain `number`
 * and tagged `NumericLiteral` leaves as equal when their numeric values
 * agree. Used for match-binding consistency and pattern literal checks.
 */
function deepEqual(a: Json, b: Json): boolean {
  if (a === b) return true
  const av = numericValue(a)
  const bv = numericValue(b)
  if (av !== undefined || bv !== undefined) return av !== undefined && av === bv
  if (Array.isArray(a) && Array.isArray(b)) {
    if (a.length !== b.length) return false
    for (let i = 0; i < a.length; i++) if (!deepEqual(a[i], b[i])) return false
    return true
  }
  if (isObject(a) && isObject(b)) {
    const ak = Object.keys(a)
    const bk = Object.keys(b)
    if (ak.length !== bk.length) return false
    for (const k of ak) {
      if (!Object.prototype.hasOwnProperty.call(b, k)) return false
      if (!deepEqual(a[k], b[k])) return false
    }
    return true
  }
  return false
}

/**
 * Attempt to structurally match `pattern` against `node`, treating any
 * bare string in `params` as a wildcard metavariable. On success the
 * `bindings` map is populated (param → bound sub-AST for operand/`args`
 * positions, param → matched literal for scalar fields) and `true` is
 * returned. Repeated occurrences of a metavariable must bind consistently.
 *
 * Pattern object fields are matched by key; node keys absent from the
 * pattern are ignored (so a partial operator pattern listing only
 * `op`/`args`/`dim` still matches a node that carries extra fields).
 */
function matchPattern(
  pattern: Json,
  node: Json,
  params: Set<string>,
  bindings: Record<string, Json>,
): boolean {
  // Metavariable: binds to whatever node occupies this position (sub-AST
  // in an operand/`args` slot, literal in a scalar field).
  if (typeof pattern === 'string' && params.has(pattern)) {
    if (Object.prototype.hasOwnProperty.call(bindings, pattern)) {
      return deepEqual(bindings[pattern], node)
    }
    bindings[pattern] = node
    return true
  }
  // Literal string (a concrete op name / variable reference): exact match.
  if (typeof pattern === 'string') return pattern === node
  // Numeric literal (plain or tagged): match by value.
  if (typeof pattern === 'number' || isNumericLiteral(pattern)) {
    const pv = numericValue(pattern)
    const nv = numericValue(node)
    return pv !== undefined && pv === nv
  }
  // Array (an `args`/operand list): element-wise, equal length.
  if (Array.isArray(pattern)) {
    if (!Array.isArray(node) || node.length !== pattern.length) return false
    for (let i = 0; i < pattern.length; i++) {
      if (!matchPattern(pattern[i], node[i], params, bindings)) return false
    }
    return true
  }
  // Object (an operator node): node must be an object that carries every
  // key the pattern specifies (extra node keys are allowed).
  if (isObject(pattern)) {
    if (!isObject(node)) return false
    for (const k of Object.keys(pattern)) {
      if (!Object.prototype.hasOwnProperty.call(node, k)) return false
      if (!matchPattern(pattern[k], node[k], params, bindings)) return false
    }
    return true
  }
  // null / boolean.
  return deepEqual(pattern, node)
}

/**
 * Try each auto-applied `match` rule (in declaration order) against
 * `node`. The first rule whose pattern matches fires: its `body` is
 * instantiated by substituting the bound metavariables and returned.
 * Returns `undefined` when no rule matches. The instantiated body is NOT
 * re-scanned by the caller (single-pass, no recursion — esm-spec §9.6.3).
 */
function applyMatchRules(node: Json, matchRules: MatchRule[]): Json | undefined {
  for (const rule of matchRules) {
    const bindings: Record<string, Json> = {}
    if (matchPattern(rule.match, node, rule.params, bindings)) {
      return substitute(rule.body, bindings)
    }
  }
  return undefined
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

/**
 * Reject a `match` rule whose `body` re-introduces its own pattern.
 * Because replacements are not re-scanned this never loops at runtime,
 * but the spec (§9.6.3) rejects such rules statically so authors do not
 * silently rely on multi-pass fixpoint rewriting. Only operator (object)
 * patterns are scanned — a bare-metavariable pattern matches everything
 * and has no structural form to re-introduce.
 */
function assertTerminating(
  match: Json,
  body: Json,
  params: Set<string>,
  name: string,
  scope: string,
): void {
  if (!isObject(match)) return
  const reintroduces = (subtree: Json): boolean => {
    if (matchPattern(match, subtree, params, {})) return true
    if (Array.isArray(subtree)) return subtree.some(reintroduces)
    if (isObject(subtree)) return Object.keys(subtree).some((k) => reintroduces(subtree[k]))
    return false
  }
  if (reintroduces(body)) {
    throw new ExpressionTemplateError(
      'rewrite_rule_nonterminating',
      `${scope}.expression_templates.${name}: match rule 'body' re-introduces its own 'match' pattern; single-pass rewriting forbids this (esm-spec §9.6.3)`,
    )
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
    const body = (decl as { body: Json }).body
    assertNoNestedApply(body, name, '/body')
    const match = (decl as { match?: Json }).match
    if (match !== undefined) {
      assertTerminating(match, body, seen, name, scope)
    }
  }
}

function expandApply(
  node: Record<string, unknown>,
  templates: Templates,
  matchRules: MatchRule[],
  scope: string,
): Json {
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
  // they cannot themselves call templates internally). Auto-applied
  // `match` rules also fire inside binding arguments.
  const resolvedBindings: Record<string, Json> = {}
  for (const [k, v] of Object.entries(bindings)) {
    resolvedBindings[k] = walk(v, templates, matchRules, scope)
  }
  return substitute(decl.body, resolvedBindings)
}

/**
 * Single bottom-up rewrite pass: expand `apply_expression_template` nodes
 * and auto-apply `match` rules. Children are rewritten first; the node
 * itself is then offered to the `match` rules (declaration order, first
 * match wins). A rule's instantiated body is returned as-is — it is never
 * re-scanned (esm-spec §9.6.3).
 */
function walk(node: Json, templates: Templates, matchRules: MatchRule[], scope: string): Json {
  if (Array.isArray(node)) {
    return node.map((c) => walk(c, templates, matchRules, scope))
  }
  if (isObject(node)) {
    // Explicit template invocation is expanded in place; its substituted
    // body is not re-walked (the bindings were already walked).
    if (node.op === APPLY_OP) {
      return expandApply(node, templates, matchRules, scope)
    }
    // Bottom-up: rewrite the children first.
    const out: Record<string, unknown> = {}
    for (const k of Object.keys(node)) {
      out[k] = walk(node[k], templates, matchRules, scope)
    }
    // Then offer this (rewritten) node to the auto-applied match rules.
    if (matchRules.length > 0) {
      const rewritten = applyMatchRules(out, matchRules)
      if (rewritten !== undefined) return rewritten
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

/** True if any model / reaction_system declares an expression_templates block. */
function hasExpressionTemplatesBlock(root: Record<string, unknown>): boolean {
  for (const compKind of ['models', 'reaction_systems'] as const) {
    const comps = root[compKind]
    if (!isObject(comps)) continue
    for (const comp of Object.values(comps)) {
      if (isObject(comp) && isObject(comp.expression_templates)) return true
    }
  }
  return false
}

/**
 * Rewrite all `expression_templates` in the given file: expand explicit
 * `apply_expression_template` nodes AND auto-apply `match` rules in a
 * single bottom-up pass per component (in place is OK — we mutate a
 * clone). Returns a new file object with templates applied and
 * `expression_templates` blocks removed.
 *
 * Pre-condition: the input has been schema-validated.
 */
export function lowerExpressionTemplates<T extends object>(file: T): T {
  rejectExpressionTemplatesPreV04(file)

  if (!isObject(file)) return file
  const root = file as Record<string, unknown>

  // Scan globally for apply ops (orphan-op detection) and for any
  // expression_templates block (a component may carry `match` rules that
  // must run even when there are no apply ops).
  const globalOps = findStrayApplyOps(file)
  if (globalOps.length === 0 && !hasExpressionTemplatesBlock(root)) {
    // Nothing to expand and no rules to apply; strip empty
    // expression_templates blocks for canonical-form invariance and return.
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
      // Templates without `match` are invoked explicitly via
      // apply_expression_template; templates with `match` are auto-applied
      // rewrite rules collected in declaration order.
      const templates: Templates = {}
      const matchRules: MatchRule[] = []
      if (isObject(tplRaw)) {
        const all: Templates = {}
        for (const [tname, tdecl] of Object.entries(tplRaw)) {
          all[tname] = tdecl as TemplateDecl
        }
        validateTemplates(all, `${compKind}.${compName}`)
        for (const [tname, decl] of Object.entries(all)) {
          if (decl.match !== undefined) {
            matchRules.push({
              name: tname,
              params: new Set(decl.params),
              match: decl.match,
              body: decl.body,
            })
          } else {
            templates[tname] = decl
          }
        }
      }
      // Walk every property except expression_templates (we don't
      // expand inside template bodies — those are validated above).
      for (const k of Object.keys(comp)) {
        if (k === 'expression_templates') continue
        comp[k] = walk(comp[k], templates, matchRules, `${compKind}.${compName}.${k}`)
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
