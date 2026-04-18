# Critical Review — RFC: Language-agnostic Discretization in ESM

**Reviewer:** radrat (polecat)
**Reviewing:** [`docs/rfcs/discretization.md`](discretization.md) (639 lines, merged via gt-dq0f)
**Bead:** gt-tlw2
**Date:** 2026-04-18

## Summary

The RFC sketches a plausible three-section extension (`grids` /
`discretizations` / `rules`) but ships a design that is not yet self-consistent
and that under-specifies the critical path for its own acceptance criteria.
Five categories of problems dominate: (a) duplication and unreconciled overlap
with features **already in the spec** (`index`, `domains.boundary_conditions`,
`data_loaders`); (b) the "bit-identical cross-binding AST" claim in §12 relies
on canonical-form machinery that does not exist in the conformance harness;
(c) the rule engine's pattern-match and termination semantics are not pinned
down tightly enough for two independent implementations to agree; (d) several
grid families the RFC claims to cover (MPAS variable-valence, cubed-sphere
seam transforms, time-dependent BCs from loaders) have no concrete mechanism
in the proposed schema; (e) the rollout steps omit the infrastructure work
(rule engine, canonical form, arrayed-variable schema) on which later steps
depend. The current document is a better motivation-and-shape doc than a
spec; it needs another pass before Step 1 should start.

## Critical issues (would block acceptance)

### C1. `idx` vs existing `index` — an unjustified second access op

RFC §5.1 (lines 95–121) introduces `idx` and justifies it as:

> `idx` references a single element of an array-valued variable or metric
> array. It is the scalar-world counterpart to `index` (§4.3.3): `index`
> operates inside `arrayop.expr`, where index symbols are local; `idx`
> operates in any expression context, and its `indices` are ordinary
> `Expression` values …

This misreads the existing spec. `esm-spec.md` §4.3.3 (lines 292–299)
explicitly says:

> `args[1..]`: one index expression per dimension. Each index is an
> `Expression`, so it may be an integer literal, a symbolic index variable
> (as a string, when inside an `arrayop.expr`), or a composite expression
> (e.g. `{ "op": "+", "args": ["i", 1] }` for an offset stencil point).

Nothing in §4.3.3 restricts `index` to live inside `arrayop.expr`. The
parenthetical "as a string, when inside an `arrayop.expr`" qualifies only
the *symbolic-index-variable* interpretation of a bare string, not the op
itself. `index` already accepts integer literals and composite index
expressions, which is exactly what `idx` is advertised as adding.

Consequences of shipping `idx` anyway:

1. Every binding gains a parallel implementation of `substitute`,
   `free_variables`, `evaluate`, `simplify` for the new op, more than
   doubling the §5.1 traversal surface.
2. Round-trippers must decide whether to emit `index` or `idx` for
   post-discretization output, creating a canonicalization choice whose
   answer is not specified.
3. The conformance harness now has to treat `idx` and `index` as either
   interchangeable (new AST-equivalence rule) or distinct (and then
   discretization output is not comparable to hand-written arrayop fixtures).

**Recommendation.** Extend `index` — either by relaxing the unwritten
(and, per §4.3.3, nonexistent) "only inside `arrayop.expr`" rule, or by
adding whatever §5.1 validation rule (b) requires. Do not introduce `idx`.

If the RFC insists on a separate node, it owes a concrete argument for why
extending `index` is wrong — the current text argues only against a straw
reading of §4.3.3.

### C2. BCs duplicate `domains.<d>.boundary_conditions` with no reconciliation

The RFC proposes (§8.2, lines 411–438) a model-level `boundary_conditions`
section "structurally parallel to `coupling`", with `bc` ops carrying `kind`
and `side` fields, rewritten by rules.

But `esm-spec.md` §11.5 (lines 2085–2106) **already** defines BCs — at the
*domain* level, with types `constant`, `zero_gradient`, `periodic`,
`dirichlet`, `neumann`, `robin`, plus fields `value`, `function`,
`robin_alpha`, `robin_beta`, `robin_gamma`.

§10 of the RFC ("Interaction with existing sections") lists `domains` as
"Unchanged" (line 474). It does not mention `domains.boundary_conditions`
at all. So the RFC silently ships a second BC mechanism without saying:

- Whether domain BCs still apply when a model is bound to a grid.
- Which wins if a model has `domain.boundary_conditions: [{type:"periodic"}]`
  *and* the discretization rules match a different BC on the same dim.
- How a pre-RFC `.esm` file with `type: "periodic"` on a domain gets
  translated into the RFC's `dim_is_periodic` guard at rewrite time.
- Whether the RFC's `bc` op is expected to be emitted by tooling that today
  only knows about `domain.boundary_conditions`.

Either retire `domain.boundary_conditions` (then the RFC is non-additive and
the 0.2.0 label is wrong) or specify a mapping (then it belongs in this
document). The current silence is not a position.

### C3. Cross-binding bit-identity relies on canonical form that does not exist

§12 (lines 508–525) claims:

> Because coefficients are kept symbolic, bit-identity across bindings is
> tractable: it reduces to AST equality after canonical ordering (addition
> associativity, commutativity normalized as in the existing harness).

The existing harness (`tests/conformance/README.md`) defines the round-trip
contract as serializer idempotence within **one** binding, explicitly
comparing JSON values after one and two passes through that binding's own
save/load. It does not define, and the codebase does not implement, a
canonical normal form for `+`/`*` associativity or commutativity across
bindings.

Every Step 1–5 acceptance criterion of the form "Julia + Rust emit
bitwise-identical AST" depends on that normal form existing. At present it
does not.

The RFC either needs to:

(a) define the canonical form normatively in the spec (argument order by
some total order on subexpressions; nesting convention for n-ary `+`;
integer / float promotion rule; zero/identity elimination; etc.); or

(b) drop the "bitwise-identical" claim and replace it with a weaker
equivalence (e.g., algebraic equivalence verified by a numerical probe on
a set of seed values).

Either is fine. Neither is in the RFC.

The choice is also not independent of C1: if `idx` and `index` coexist,
the canonical form must pick one.

### C4. Metric-array `loader` references a non-existent extension to §8

RFC §6.5 (lines 278–287) and the MPAS example in §6.3 (lines 222–244) use:

```json
{ "kind": "loader", "name": "mpas_mesh", "params": { "field": "dcEdge" } }
```

…and describe this as "Names a registered loader (§8 of the spec)".

But `esm-spec.md` §8 (lines 1364–1469) describes data-loaders as
STAC-style gridded/point-data sources, keyed under a top-level
`data_loaders` map, addressed by their *key* (not a `name` field), with
sub-variables nested under `variables` (not a `params.field`). And §8.7
explicitly states:

> Mesh connectivity for unstructured grids. `kind: "points"` is a
> placeholder for future work.

So the RFC proposes an MPAS mesh loader that the base spec explicitly
defers. Three gaps result:

1. The RFC's `{kind, name, params}` syntax is inconsistent with existing
   data-loader addressing.
2. The spec extensions required to make Step 4 possible (a mesh-loader
   `kind`, connectivity output contract, determinism guarantees) are not
   enumerated in §16 (Deliverable checklist) and are not scheduled in §13.
3. `loader.params.field` implies multiple logical fields per loader —
   incompatible with the existing "one schema-level var per `variables`
   entry" model.

Step 4's "Full MPAS `x1.2562` mesh loads and discretizes without error" is
un-provable until this is fixed.

### C5. Pattern-match semantics are not pinned down

§5.2 (lines 123–152) specifies three fields (`pattern`, `where`,
`replacement`) and a guard vocabulary, then asserts "Order of application
is deterministic: rules are applied in the order listed under `rules`;
within one pass, earlier subtrees are rewritten before later ones. This
is sufficient for the schemes enumerated in §8 and produces
bitwise-identical output across bindings."

Questions the RFC must answer before two bindings can agree:

1. **What does a pattern variable bind to?** A leaf variable name? Any
   subtree? The examples at lines 376 and 428 use `"args": ["$u"]` where
   `$u` appears positionally — is that pattern matching a single arg whose
   value is any Expression, or only a bare string? In the guard
   `var_has_grid`, `$u` must resolve to "a variable" — so the answer must
   be "a variable name string" for that rule, but "any subtree" is plausible
   elsewhere (e.g., what would `{op:"grad", args:["$u"], dim:"$x"}` match
   if `$u` is `{op:"*", args:["rho","u"]}`?).

2. **Non-linear patterns.** If `$u` appears twice in `pattern`, must both
   occurrences be AST-equal? Byte-equal (post-canonicalization)? The RFC
   does not say.

3. **Associative / commutative ops.** Does `{op:"+", args:["$a","$b"]}`
   match a three-operand sum? Match commutatively against `b + a`? Against
   `b + a + c` with `$b := a + c`? Each binding's symbolic stack (Julia's
   SymbolicUtils vs. Rust's hand-rolled) has a different default. The
   existing ESM `+` is n-ary (spec §4.2, line 101). This interacts
   catastrophically with C3.

4. **Pattern variables in non-`args` fields.** §7 (line 306) uses
   `"applies_to": {"op":"grad","dim":"$x"}` — `dim` is a sibling of `op`,
   not an entry of `args`. Are pattern variables legal in sibling fields?
   Which sibling fields? The spec's `op:"D"` has `wrt`, `op:"broadcast"`
   has `fn`, etc. Enumerate.

5. **Termination.** "Two-pass fixed-point loop" (line 147) does not
   protect against a rule whose `replacement` re-introduces its own
   `pattern` (either directly or via another rule). The RFC owes a
   termination rule. Options: (i) a rewritten subtree is not re-matched
   by any rule in the remainder of that pass; (ii) a rewritten subtree
   is not re-matched by the *same* rule in the remainder of the pass;
   (iii) a fixed iteration budget. Each gives different answers on
   cascading BCs (§8.3 `produces: ghost_var`).

Without explicit answers, two bindings will diverge on the first
nontrivial scheme and Step 1 is unverifiable.

## Major issues (need resolution before Step 1)

### M1. `dx` scalar vs `dx[i]` indexed — the scheme selector is missing

§6.2 (lines 217–220): "`extents[<dim>].spacing` — `"uniform"` lets rules
assume a scalar `dx`; `"nonuniform"` forces the rule to emit `dx[i]`
(indexed) references." But the example scheme `centered_2nd_uniform`
(§7, line 309) writes the coefficient as `"dx"` — a bare string, scalar.
How does that same scheme become `idx(dx, [target.x + offset])` on a
non-uniform grid?

Three possibilities, none specified:

(a) Author writes two schemes (`centered_2nd_uniform` and
`centered_2nd_nonuniform`), and two rules with `dim_is_nonuniform` guards
select among them. Then the guard `dim_is_nonuniform` must exist, but §5.2
doesn't list it.

(b) Discretization engine automatically rewrites scalar `"dx"` references
to `idx("dx", [...])` when `spacing = "nonuniform"`. Then the rewrite is
context-sensitive on the scheme's operand-axis binding. §7.2 does not
describe this.

(c) The scheme name `centered_2nd_uniform` is load-bearing and only matches
uniform grids by convention. Then there is no mechanism for the
conformance harness to reject a misuse, and Step 3 fails silently.

Pick one; write it down. Step 3 cannot land without.

### M2. MPAS variable-valence operators have no stencil representation

§7 (lines 314–328) shows `mpas_edge_grad` as a *two-entry* `stencil`
array. That works for a gradient at an edge (two cells). But a
**divergence at a cell** on MPAS requires a reduction over
`edgesOnCell[c, 0 .. nEdgesOnCell[c] - 1]` — a variable-length list of 5
or 6 edges (pentagons at the 12 icosahedral vertices, hexagons elsewhere).

The `stencil` field is an array of fixed `{selector, coeff}` entries. It
cannot express "reduce over `edgesOnCell[c, k]` for `k ∈ 0 .. K(c)`". The
RFC does not propose a reduction selector.

Workarounds the RFC implicitly offers, and their problems:

- **Emit the divergence as an `arrayop`** with a contracted index `k` over
  the `edgesOnCell` row. Then the "stencil template" abstraction is
  bypassed and §4 of the RFC (line 68: "All three target grid families
  reduce to a single stencil template") is overclaimed — MPAS does not
  reduce to that template.
- **Hardcode a max-valence stencil** (10 entries, mask out unused). But
  `maxEdges = 10` (line 241) is a loader-reported quantity, not known at
  schema-authoring time; and the mask emission mechanism doesn't exist.

Step 4 ("MPAS edge-gradient + cell-divergence") is blocked.

### M3. `mpas_edge_grad` target binding is not explained

The same scheme (§7, lines 314–328) uses `"$e"` inside `indices: ["$e", 0]`
for the `cellsOnEdge` lookup. `$e` is not a pattern variable bound by any
`applies_to` (line 315 shows `{op:"grad", dim:"edge"}` — no `args`). Where
does `$e` come from? The RFC §7.2 expansion mechanism says `materialize`
uses `$target`, not `$e`. Either `$e` is an implicitly-bound synonym for
the output index of the scheme, or the example is wrong.

### M4. Panel seam `axis_flip` cannot represent cross-panel axis swaps

§6.4 (lines 250–269) declares `axis_flip` with `shape: [6, 4]`, `rank: 2`
— i.e., each `(panel, side)` pair stores a single integer. The physical
quantity being stored is the local axis transformation applied when a
stencil stepped in (+i, 0) on panel P ends up on panel Q, where the i-axis
of P may correspond to +j, −j, +i, or −i on Q.

That's an element of the dihedral group D₄ (or equivalently a signed
permutation of two axes: 8 elements). A single integer can enumerate
those, but the RFC's §7.2 expansion (lines 356–362) says only "apply
`axis_flip` to (di, dj)" — it does not define the group action. Two
bindings implementing different conventions (row-major vs. column-major,
CCW vs. CW, sign-first vs. swap-first) produce different index
expressions.

Step 5 ("FV-flux scheme parity with EarthSciDiscretizations.jl") cannot
be verified without the group action pinned.

### M5. Time-dependent BCs from data loaders — mechanism unspecified

§8.2 (lines 418–420) allows BC replacement AST to reference
"Data-loader sources (`observed_SST`)". But a data loader produces a
runtime-resolved, time-varying field. At rewrite time — which is *static*
— there is no way to ground `observed_SST(t, x, y)` into an AST node.

Questions:

1. Is `"observed_SST"` a bare string that the assembler later wires to
   a runtime handle? How does the rewriter know to treat it as array-
   valued (so `idx` indices must be attached) vs. scalar?
2. Where does `t` come from in the emitted equation? Implicit? If so,
   how is the implicit `t`-binding expressed in the AST?
3. Can the BC depend on both time (`t`) and space (the BC's side/location)?
   The spec's `{op:"bc", args:["$u"], kind:"dirichlet", side:"xmin"}`
   pattern doesn't expose a face-coordinate index.

The RFC task prompt specifically flags this as a required case. It is
not covered.

### M6. Arrayed state variables have no schema

§11 (line 504–506) says:

> Step 5 output is still ESM-representable: it is a `models` entry with
> arrayed variables plus algebraic constraints, no new node types
> introduced. A `discretized: true` boolean on the output model is the
> only metadata change.

But `esm-spec.md` §6.1 (lines 697–798) and §6.3 (lines 816–822) define
`variables.<name>` with `type ∈ {state, parameter, observed}`, all
scalar-valued. There is no dimension/shape field. A post-discretization
model has `u` at `(Nx, Ny, Nz)`. How is that encoded in an ESM file
today? Silent answer: it isn't.

§16 does not list any schema addition to `variables.<name>` to carry
shape. §13 does not schedule such a change. Without it, step 1's output
is unrepresentable.

### M7. Step 1 acceptance criterion depends on an external PR

§13 Step 1 (lines 538–545) anchors acceptance on reproducing
`MethodOfLines.jl PR #531`'s `ArrayDiscretization` output. That PR is
external to this repo, may change, may be rejected, and is not
version-pinned in the RFC. "Polecat knows when step 1 is done" requires
reading a moving upstream target.

Pin the PR by commit SHA, or capture the expected outputs as fixtures
under `tests/conformance/discretization/` and state acceptance as
"fixtures pass" rather than "reproduces PR #531".

### M8. The rule engine / canonical form steps are missing from §13

§13 schedules 5 rollout steps, but the RFC never schedules:

- Implementing the §5.2 rule engine. Step 1 simply says "Cartesian
  neighbor selector only. `idx` AST node in all five bindings." — but
  the rule engine is what *fires* those selectors. Where does it land?
- Defining and implementing the canonical AST form required by §12 (see
  C3). This is pre-requisite to *every* step's bit-identity criterion.
- Adding the arrayed-variable schema (see M6).
- Adding the BC op and the `bc` pattern syntax at the spec level. Step 2
  treats these as schema additions but §16 (Deliverable checklist) folds
  them under a single "gains JSON-schema entries for the pattern-variable /
  guard sub-schema" bullet, not per-step additions.

Restructure §13 to put infrastructure in Step 1 and schemes in Steps 2–5.

## Minor issues (worth fixing)

### m1. Grid extents duplicate `domains.<d>.spatial.<dim>.grid_spacing`

`esm-spec.md` §11.3 (line 2069) gives `spatial.<dim>.grid_spacing` (a
scalar). RFC §6.2 (lines 196–213) re-encodes this as
`extents.<dim>.{n, spacing}`. If a grid names a domain (§10, line 474),
the two can contradict. Specify priority or remove one.

### m2. `panel` selector fields (`panel_rel`, `di`, `dj`) have no worked example

§4 table (line 82) names the fields; §6.4 example doesn't use any of
them in a stencil; §7 has no panel-selector stencil at all. Add a
minimal panel-selector example — otherwise Step 5 starts from a blank
page.

### m3. `metric_arrays.dxC.generator.expr = "<analytic on cube>"`

§6.4 (lines 263–265) uses a placeholder string where an ESM AST
expression belongs. Either show a concrete cubed-sphere metric (even a
sketch), or the RFC has tacitly taken a position that analytic
cubed-sphere metrics are infeasible without new AST operators (sin,
cos, atan2 all exist — so they aren't).

### m4. Guard-name inconsistency

§5.2 table (lines 137–144): `var_is_spatial_dim_of` is about a *dim*,
not a var. Rename to `dim_is_spatial_dim_of` or similar for consistency
with `dim_is_periodic`.

### m5. Staggered-location assignment responsibility is vague

§9 (lines 461–466): "The staggering tag is added during the
spatialization step — it is not hand-authored on pre-spatialization
continuous models." Who runs this step, with what inputs? Is
spatialization itself a new ESM pipeline stage, or a tooling concern
outside the spec? If the former, it belongs in §11 (pipeline).

### m6. Pattern-matcher closed vocabulary risks

§14 risk 1 acknowledges the closed guard vocabulary but doesn't list
obvious gaps scheme authors will hit on day one:

- Negation ("operand is *not* a constant")
- Constant-folding guards ("pattern variable is a numeric literal")
- Arity guards ("matches a 2-operand `+`, not n-ary")
- Structural guards ("pattern variable contains `D` anywhere in its
  subtree")

Call these out as "known limitations, out of MVP" or add them.

### m7. §13 Step 3 CSV loader uses a loader kind that doesn't exist

"Metric arrays declared with `generator.kind = "loader"` (CSV loader for
prototype)" — the CSV loader is an implementation detail, not a schema
object. Either the loader registry is a spec artifact (then enumerate
it) or it's a runtime binding concern (then don't promise a CSV loader
by name).

### m8. §3 table says `rules` is a "composition" of the three sections, but §7.2 shows schemes alone expanding patterns

`discretizations` in §7 has its own `applies_to` pattern (lines 304,
306). So pattern matching happens both at the rule level (§8) and inside
the scheme (§7). Is a scheme's `applies_to` matched against the post-
rule-substitution subtree, or is the rule a pure "scheme selector" that
only fires when the scheme's own `applies_to` matches? The two-stage
matching is not explained.

### m9. `produces: state_var` (§8.3) is not justified

`algebraic` and `ghost_var` both have concrete use cases (Dirichlet
closure, high-order stencils). `state_var` ("Promote to a differential
state variable") has no example — when would a BC rule emit a new
differential state? Remove it from the MVP or demonstrate the case.

## Questions the RFC should answer but doesn't

1. **Is the rule-engine's output deterministic across bindings in the
   presence of nested schemes?** If rule R1 rewrites `grad(u)` to an
   expression containing `grad(w)`, and R2 rewrites `grad(w)`, in what
   order? Top-down then top-down again? Inside-out?

2. **Schema-validation reach.** What does the JSON-schema actually
   catch for the new sections? Rule-cycle detection, pattern-variable
   scoping, guard well-formedness, `use` vs. `emit` exclusivity, grid /
   scheme compatibility, grid-parameter reference resolution — which of
   these are encodable in JSON Schema, and which are deferred to the
   loader?

3. **What happens when `models.<M>.grid` is set but no rules match an
   equation?** Silent pass-through, error, or warn? The pipeline (§11)
   doesn't say. Most likely answer is "the rule engine leaves the
   equation alone" — but then authoring `rules` is error-prone (typos
   silently skip rewrites).

4. **How are discretization outputs cached?** §11 step 3 says
   expression-kind metric generators are "evaluate[d] and cache[d]".
   Across sessions? Per-binding? The existing spec has no cache concept.

5. **ModelingToolkit interop assumption.** §11 Step 5 ("Collect") hands
   the discretized equations to "the host language's ODE/DAE
   assembler". For Julia, that's MTK. For Rust/Go/Python/TS — what? The
   RFC assumes they all have DAE assemblers with equivalent capability.
   That assumption needs a paragraph of its own — especially for the
   `produces: algebraic` case.

6. **Interaction with `coupling.<c>.variable_map.transforms`.** If
   model A (continuous) is coupled to model B (continuous), both bound
   to grids, the translate step on the continuous variables happens
   *before* rewrite. Does the rewrite then run per-model, or
   post-coupling? §10 says "the discretized pipeline applies rules to
   both sides before solving" — which implies post-coupling, but then
   cross-model indices (grid A → grid B) appear on one side of the
   coupling equation. There is no mechanism for cross-grid index
   expressions.

## Alternatives not discussed

The task prompt specifically calls out these; all are missing from §15:

1. **MLIR / StableHLO as the discretized IR.** Rejected reason would
   presumably be "introduces a non-JSON format" — but the RFC could
   emit MLIR text and still keep the .esm file as authoring surface.
   The alternative deserves a paragraph.

2. **Reuse SymPy's existing rule DSL (serialized).** SymPy has
   `Wild`/`Replacer` constructs with well-tested semantics. The RFC's
   §5.2 pattern language reinvents a subset of this. Worth comparing
   the feature gap.

3. **OpenFOAM-style field-operator formalism.** `fvc::grad(p)` on a
   mesh with stored boundary conditions; the operator selects the
   scheme from a `fvSchemes` dict. This is closer architecturally to
   what the RFC proposes than the §15 rejected alternatives.

Additional alternatives the RFC also didn't consider:

4. **Emit as `makearray`** (spec §4.3.2) — the RFC rejects
   "fully-materialized `arrayop`" (§15, lines 618–620) but does not
   consider `makearray` with a single region and an `arrayop` body,
   which compresses the "one stencil expression per interior cell"
   into O(1) text for rectangular grids (only the BC regions grow).

5. **Reuse the existing `operators` section (spec §9)** to register
   discretization operators as opaque runtime transforms, with a
   schema-level descriptor of their input/output. This is architect-
   urally the minimum viable RFC; §2 "Non-goals" does not forbid it.

## Suggested next steps

In order:

1. Resolve C1 (pick `index` or `idx`) and C2 (reconcile BCs with
   §11.5). Both are single-author decisions; they do not require
   investigation.

2. Write a "Canonical AST form" sub-section of §5 (or a new §5.4)
   that normatively defines the normal form required by §12. Without
   this, no Step's acceptance criterion is verifiable.

3. Pin the §5.2 pattern-match semantics (answers to C5.1–5). A one-
   page worked example "here is the rule firing on this tree, with
   each binding's rewritten output byte-for-byte" would catch most of
   the ambiguity.

4. Decide whether MPAS variable-valence operators are in scope (M2).
   If yes, add a reduction selector. If no, declare explicitly in §13
   Step 4 scope that only fixed-valence cases are covered.

5. Rewrite §13 to schedule infrastructure (rule engine, canonical form,
   arrayed-variable schema, BC op) in Step 1, and move "Julia + Rust
   bit-identical on 3 fixtures" to the end of Step 1 rather than its
   acceptance criterion.

6. Cut the `idx` vs `index` ambiguity (C1) from the deliverable in §16
   and replace with "extend `index`'s documented permitted contexts".

7. Address M3 (`$e` in mpas_edge_grad), M4 (axis_flip group action),
   and M5 (time-dependent BCs) with concrete worked examples, or
   descope them from the corresponding rollout steps.

Once items 1–3 are addressed, a second review can focus on the schema
additions themselves. As it stands, too many load-bearing semantics live
in prose or are absent.
