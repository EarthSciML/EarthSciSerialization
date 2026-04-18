# Parallel Independent Review — Discretization RFC v2

**Reviewer:** polecat `ghoul` (fresh eyes — no prior involvement with v1 or v2)
**Document:** `docs/rfcs/discretization.md`, 1386 lines, dated v2 (revision of v1 per review `gt-tlw2`)
**Bead:** `gt-adhm`
**Date:** 2026-04-18
**Companion review:** `docs/rfcs/discretization-review-v2.md` (by brahmin, RFC author)

---

## Summary

v2 is a substantial improvement over what §17 suggests v1 was, but it is **not ready for Step 1
as written**. The RFC has strong architectural bones — three selector kinds, a closed guard
vocabulary, an explicit pipeline, a worked MPAS example — but three categories of problem
block Step 1 acceptance: (i) the bit-identity story (§5.4) is incomplete because it inherits
JSON float-formatting from each host language's encoder, (ii) multiple normative statements
contradict each other (notably §7.1.1 `$target` vs. §7.3's worked MPAS expansion), and (iii)
at least four ambiguities (dim-to-component mapping, `regrid.method` selection, BC face-coord
binding, scheme `applies_to` vs. rule `pattern` interaction) would cause two independent
implementers to diverge. Targeted fixes — roughly ten pinpoint spec additions — can land on
top of v2 without a v3.

---

## Issues found on first read

Every finding cites RFC line numbers. Findings are ordered by severity (**C**ritical,
**M**ajor, **m**inor), then by appearance in the document.

### C1. Bit-identity claim hinges on unspecified float serialization (§5.4.2, lines 318–329)

§5.4.2 defines non-leaf ordering by "stable serialization: recursively canonicalize, then
compare their JSON serializations as byte strings (UTF-8, sorted keys, no extraneous
whitespace)" (lines 326–328). §13.1 Step 1 acceptance requires all five bindings to produce
"byte-identical canonical form" (line 1041).

**Gap:** the RFC specifies key ordering, UTF-8, and whitespace — but **not** the textual
formatting of numeric literals. Julia's `JSON3`, Rust's `serde_json`, Python's `json`, Go's
`encoding/json`, and TypeScript's `JSON.stringify` all produce different representations of
the same `Float64` (e.g. `1e10` vs `10000000000`, trailing zeros, minimum-precision
shortest-round-trip vs. full 17-digit, `NaN`/`Infinity` handling, negative zero). Without a
normative float-format rule, §13.1 Step 1 acceptance is **infeasible** on fixtures that
contain any float.

**Fix:** add §5.4.6 (or extend §5.4.1) with a normative number-formatting rule analogous to
RFC 8785 / JCS (e.g. shortest round-trip IEEE-754 decimal, `"1"` not `"1.0"` for integer-valued
floats iff type is integer, fixed exponent form for magnitudes outside `[1e-6, 1e21]`, etc.).
Pin the rule explicitly, with a worked example.

### C2. §7.1.1 `$target` table contradicts the §7.3 worked MPAS example (lines 650–660 vs. 686–733)

§7.1.1 (line 654) says for `unstructured`, `$target` is "one of `c` (cell), `e` (edge),
`v` (vertex) — **chosen by the operand's `location`**". The MPAS divergence scheme in §7.3
has `requires_locations: ["edge_normal"]` (line 695), so per §7.1.1 `$target` should bind to
`e`. But the §7.3 expansion at line 720 ("Expansion at cell `c`") and every `$target`
substitution in the emitted `arrayop` (lines 725, 729, 730, 731) uses `c`, i.e. **the output
location** (`emits_location: "cell_center"`, line 696), not the operand's.

This is a direct contradiction of a normative rule, and it sits on the single worked example
meant to establish MPAS interoperability. Two implementers reading §7.1.1 vs. §7.3 will
produce different AST. `c`-vs-`e` disagreement also propagates into every `index(edgesOnCell,
$target, k)` — connectivity addressing.

**Fix:** the rule is "choose by `emits_location` if set, else by operand's `location`".
State that in §7.1.1 and verify every worked example conforms.

### C3. Mapping from dimension names to `$target` components is unspecified (§7.1.1, §7.2)

§7.1.1 says `$target` for cartesian is `[i, j, k, ...]` (line 652). A scheme's stencil
selector has `axis: "$x"` which binds to a dimension name like `"x"`. §7.2's materialize row
for `cartesian` (line 679) says: "For target `[..., axis_idx, ...]`, output the same list with
`axis_idx` replaced by `{op:"+", args:[axis_idx, offset]}`". But **which component of
`$target` corresponds to axis `"x"`** is never stated. By positional mapping
(dimensions[0]→i, dimensions[1]→j, ...)? By name equivalence (axis "x"→`$target.x`)? By
explicit declaration elsewhere?

For the example grid in §6.2 with `dimensions: ["x","y","z"]`, the answer is "positional" —
but that's a convention, not a normative rule. A binding that implements "axis name ==
component name" will diverge on any grid whose spatial dimensions are not exactly `[x,y,z]`
in that order (e.g. `[lat, lon, lev]` for a geophysical run).

**Fix:** add one sentence to §7.2 pinning the mapping: "For cartesian grids, axis `A` in a
selector binds to the `$target` component at index `dimensions.indexOf(A)`, using the
canonical component names `[i, j, k, l, ...]` in the enumeration order of `dimensions`."
Reference this from §7.1.1.

### C4. Rule `pattern` vs. scheme `applies_to` semantics are underspecified (§5.2, §7.1, §17 m8)

§7.1 line 631: "`applies_to`: A shallow AST pattern (§5.2 syntax) identifying the operator
this scheme discretizes. Pattern variables in `applies_to` are visible to `stencil` and
`coeff`." §17 m8 (line 1360): "a rule fires first; a scheme's `applies_to` is matched against
the rule's `$u` / `$target` binding at expansion time."

Three questions a second implementer will hit, none answered:

1. **Is `applies_to` matching necessary for the scheme to expand, or just for variable
   re-binding?** §5.2.6 (lines 246–285) shows a rule with pattern `grad(args:["$u"],
   dim:"$x")` matching `grad(T, x)` and "invok[ing] the `centered_2nd_uniform` scheme". That
   scheme's `applies_to` is syntactically identical. If the rule's pattern already bound the
   variables, what does matching `applies_to` add?
2. **What if `applies_to` is strictly more specific than the rule's pattern?** E.g. rule
   `pattern = {op:"D", args:["$u"], wrt:"$x"}` but scheme
   `applies_to = {op:"grad", args:["$u"], dim:"$x"}`. Is this a loader-time rejection or a
   rewrite-time "no expansion" miss?
3. **Do pattern variables from the rule flow into the scheme by name or by position?** If
   both sides say `$u`, is that equality-by-name required? If the rule binds `$X` but the
   scheme uses `$u`, does the engine rename?

**Fix:** §7.1 or a new §7.2.1 should pin the protocol: "the scheme's `applies_to` is
re-matched against the rule-matched subtree; pattern-variable bindings from the scheme
dominate downstream expansion; if `applies_to` fails to match, the scheme is a type error
caught at loader time (not at rewrite time)." Or whatever the right rule is — but pick one.

### C5. §5.2.5 termination rule is ambiguous about rewrite-then-subtree behavior (lines 232–243)

"A new pass begins once the previous pass completes; a pass that produces no rewrites
terminates the loop" (line 238) and "the rewritten subtree is not re-matched by any rule for
the remainder of the current pass" (line 237).

Unanswered: when rule R1 rewrites subtree S to a new tree T (e.g. §7.3 lowering to
`arrayop`), does the top-down walker in the current pass:

(a) continue walking S's **original** siblings after S is replaced by T, never entering T; or
(b) continue top-down inside T (entering the children of T); or
(c) skip T entirely and resume at the post-order position after S?

Option (a) is the natural reading but makes it impossible for a scheme's output to be
further rewritten within the same pass, forcing everything into a second pass with
implications for `max_passes`. Option (b) risks rewriting the scheme's own output, which the
rule engine typically wants to prevent. Option (c) is awkward. The RFC needs to say which.

**Fix:** pin it. I'd propose (a), because it's the simplest, matches SymbolicUtils'
`Postwalk + Chain`, and preserves scheme-output immutability within a pass.

### M1. `regrid.method` is an unconstrained string; bit-identity unreachable (§5.3, lines 287–303)

"`method` names a regridding algorithm that the target binding recognizes (e.g.
`"bilinear"`, `"conservative"`, `"nearest"`); the set of algorithms is not schema-validated
beyond being a string" (lines 300–302).

§13 demands bit-identical canonical AST. If `method` is author-supplied, fine — but the
RFC never describes **where `method` comes from at rewrite time**. §6.4.2's worked panel
example (line 567) emits `regrid(..., method: "panel_seam")`. That string isn't author-input;
it must be supplied by the scheme or the pipeline. If two bindings default to different
method strings for the cross-panel case, bit-identity fails.

**Fix:** either (a) require all `regrid` emissions inside materialize to carry a method name
supplied by the selector itself (add a `regrid_method` field to the `panel` selector), or
(b) enumerate a closed set of RFC-normative method names and specify which rewrites use
which.

### M2. `kind: "periodic"` BCs under-defined (§9.2 line 866)

Periodic BCs are listed as a `kind` alongside dirichlet/neumann/etc. But periodicity is
inherently a **pair** (wrap `xmin` with `xmax`), not a side-local property. The RFC shows no
rewrite template for how a rule processes a periodic BC, no worked example, and no rule on
whether you declare it once (at `xmin`) or twice (at both sides).

Since Step 1b acceptance (line 1057) specifies a "rect_1d_advection_centered_periodic" fixture,
a consumer implementing this fixture has no spec guidance on what AST the periodic BC produces
after rewrite.

**Fix:** add §9.2.1 covering periodic BCs: either declared once with an implicit paired side,
or declared as `periodic` on both sides and validated as consistent. Show one worked example.

### M3. §5.1 "bare string resolves as parameter reference" contradicts §8.A.3 `t` handling (lines 120–146 vs. 807–813)

§5.1 item (1): "Outside `arrayop.expr`, bare-string index arguments are resolved as ordinary
parameter references (§6.2 of the spec), not as symbolic index variables" (lines 122–123).

§8.A.3 step 2: `{op:"index", args:["observed_SST", "t", <face_coord_0>, ...]}` where `t` is
"the model's time variable (spec §11.3 `independent_variable`, default `"t"`), bound as a
free variable of the BC expression" (lines 807–811).

`t` is a time variable, not a parameter. And the face-coord args (typically named `i`, `j`)
are neither parameters nor arrayop indices — they're "face index names" whose binding scope
is the BC itself (§9.2 `face_coords` field).

Under §5.1, the loader must reject both cases as undeclared parameter references. Under
§8.A.3 + §9.2, the loader must accept them.

**Fix:** §5.1 needs a third resolution class: "symbolic index names declared by enclosing
BC `face_coords` or by the model's `independent_variable`". Enumerate the allowed sources
of bare-string `index` args outside `arrayop`.

### M4. `$target` for 2D+ unstructured grids is singular but stencil schemes nest index expressions over it (§7.1.1, §7.3)

§7.1.1 says unstructured `$target` is **one** of `c`, `e`, `v`. §7.3's scheme binds
`$target = c` (cell). But the scheme's coefficient expression (line 710) has
`index("dvEdge", index("edgesOnCell", "$target", "k"))` — **two levels** of `index`, with the
inner one (`edgesOnCell`) taking `c` AND `k`, and the outer one (`dvEdge`) taking an edge
index from the inner lookup.

This is fine as written for the cell-divergence scheme, but:

- (a) the text of §7.1.1 does not explain that `$target` inside a `reduction` selector
  coexists with the reduction's `k_bound` variable (`k`), which is introduced by the selector
  and bound inside the materialized `arrayop`;
- (b) a scheme author reading §7.1.1 has no cue that `k` exists as a second in-scope index
  inside the `coeff` tree.

**Fix:** §7.1 needs to state explicitly that `reduction` selectors expose their `k_bound`
variable as an in-scope index alongside `$target`, and that `$target` is a **scalar** (single
index) on unstructured grids. Ideally rename `$target` to `$target_index` and reserve
`$target_scope` for the (grid, location) tuple.

### M5. `coeff` that references `dx` but the operator is on `y` (or panel 3 of a cubed sphere) is not fence-checked (§6.2.1, lines 447–461)

§6.2.1 rewrites bare string `"dx"` inside a `coeff` to `index("dx", target-for-$x)` **only
when `spacing: "nonuniform"`**. For uniform grids, `"dx"` remains a bare scalar reference.

But a scheme like the §7 example hard-codes the **literal string `"dx"`**. If a rule matches
`grad(u, dim="y")` and the same scheme is invoked, the materialized expression references
`"dx"` — the x-spacing — when it should reference `"dy"`. The RFC has no mechanism for a
single `centered_2nd_uniform` scheme to work for both x and y.

Two realistic resolutions:

- Require authors to write one scheme per spatial dimension (`centered_2nd_uniform_x`,
  `centered_2nd_uniform_y`, ...). This is what the RFC's example implies; schemes become
  verbose.
- Allow a scheme to parameterize its metric reference on `$x`, e.g.
  `{op:"metric_for_axis", args:["$x"]}` that resolves to the dim's spacing metric. The RFC
  does not add this op.

Either choice is fine, but the RFC picks neither explicitly. Step 1b fixture
`rect_2d_diffusion_5point_periodic.esm` requires either multiple schemes or a cross-axis
mechanism; the RFC's fixture catalog suggests it "just works."

**Fix:** state explicitly in §7.1 that `coeff` is axis-specific (thus one scheme per axis is
the intended authoring pattern) **or** add an axis-parameterized metric lookup.

### M6. No canonicalization rules for `-`, `/`, `neg` (§5.4)

§5.4.2 specifies ordering only for `+` and `*`. §5.4.3 flattens only `+` and `*`. §5.4.4
eliminates `+(0,...)`, `*(1,...)`, `*(0,...)`, `/(x,1)`, `-(0)`, `-(x,0)`.

But the RFC's own worked examples emit `/(-1, *(2, dx))`, `/(1, *(2, dx))`, `-(x_max, x_min)`
in §5.2.6, §6.2, and elsewhere. Two bindings can disagree on:

- Whether `-(x, 0)` and `+(x, {op:"-", args:[0]})` are equal (they should be).
- Whether `-1` is `{type: integer, value: -1}` or `{op:"-", args:[1]}` (JSON allows both).
- Whether `1/x` is `/(1, x)` or `*(1, pow(x, -1))`.

§5.4.1's "no auto-promotion" is orthogonal; it doesn't fix these.

**Fix:** §5.4 should either (a) enumerate the canonical form for each `-`, `/`, and unary
`neg`/`-` op explicitly, or (b) state that the spec's existing §4.3 op taxonomy defines the
only allowed forms and give a normalization rule for each.

### M7. `dim` argument on `div` is a topology-type slot on unstructured grids but a spatial-axis slot on cartesian (§5.2.4, §7.3)

Guard `dim_is_spatial_dim_of` (line 220) has `pvar` binding to a dimension. For cartesian
grids, spatial dimensions are `x, y, z`. For unstructured grids, `dimensions: [cell, edge,
vertex]` (line 468) — these are topological, not spatial. The scheme in §7.3 uses `dim:
"cell"` (line 693) as the pattern's dim slot.

So `dim` is overloaded: spatial axis on cartesian, topology/output-location on unstructured.
This isn't inherently wrong but it is not stated, and a guard named `dim_is_spatial_dim_of`
will confuse authors who come from a cartesian background and see it used with `dim: "cell"`.

**Fix:** rename the guard to `dim_is_named_dim_of` (or similar) and note the dual meaning in
the pattern-vocabulary description.

### M8. Cross-binding DAE support creates silent Step 2 gap for Python/Go/TS (§12, §13.1)

§12 (lines 983–997) says a binding with no DAE assembler must abort with
`E_NO_DAE_SUPPORT` when a rewrite produces an algebraic constraint. Step 2 acceptance
(§13.1, lines 1078–1085) lists Julia+Rust bit-identity and a Julia runtime-solve, but does
**not** say what Python/Go/TS must do with the same fixture. Step 1b (line 1062) said the
three trailing bindings "must round-trip the fixtures without loss." Step 2 doesn't extend
that.

If the SST-forced Dirichlet fixture (line 1083) produces `produces: algebraic`, any binding
without DAE support errors out — fine per §12. But does that count as Step 2 acceptance-pass
or acceptance-fail for that binding? Undefined.

**Fix:** add to each of Step 2, 3, 4 a one-line disposition for the three trailing bindings:
round-trip-only, parse-only, or must-implement. Otherwise the Step-roadmap reads as "Julia
+ Rust only" after Step 1, with Python/Go/TS quietly dropped.

### m1. §5.4 byte-wise canonicalization has quadratic worst case in sort comparison (§5.4.2)

"Non-leaf nodes, sorted by a stable serialization: recursively canonicalize, then compare
their JSON serializations as byte strings" (lines 326–328). In a sort, each comparator call
triggers a full serialization of each operand. N operands → O(N log N) comparisons → O(N^2
log N) work in total AST size if the serialization of each operand is O(N). Memoization
rescues it but must be stated.

**Fix:** note that implementations should memoize the serialization at each canonicalized
node. One sentence in §5.4.2.

### m2. `panel_connectivity.neighbors` is declared under `panel_connectivity`, but §5.1's validator only knows about grid `connectivity` (lines 136–145 vs. 504–516)

§5.1's validation rule: "V must resolve to either (a) a declared variable ... or (b) a
connectivity table declared under a grid" (lines 140–145). §6.4 places cubed-sphere
connectivity under `panel_connectivity:` (line 504), not under `connectivity:`, which §6.3
reserves for unstructured (line 470).

§6.4.2's example (line 564) has `{op:"index", args:["neighbors", "p", 1]}`. By §5.1 strict
reading, this is an ill-formed reference.

**Fix:** extend §5.1's validator rule to accept `panel_connectivity.<name>` in addition to
`connectivity.<name>`.

### m3. §5.4.4 rule `+(0) → 0` vs. `+(x) → x` is inconsistent in the zero-only case (line 338)

"If only `0` remains, replace with `0`" (§5.4.4). So `+(0) → 0`. And `+(x) → x`. Consistent.
But then `+(0, 0)` first flattens (no-op), then eliminates zeros one at a time. After
elimination, `+() → 0` (line 339). Fine. But is `+(0, 0)` canonicalized by repeated single
elimination or by wholesale replacement? The order matters if `0.0` and `0` are present
together (§5.4.1 says they're distinct nodes); are both eliminated or only one?

**Fix:** one sentence: "zero elimination iterates until no numeric-zero child remains
(integer `0` and float `0.0` both qualify)."

### m4. `face_coords` declared on the BC but its relationship to `index` args is positional-implicit (§9.2, §8.A.3)

§9.2 `face_coords` "declares the reduced face-coordinate index names used when `value`
contains `index` into a loader-provided time-varying field. E.g., for `side: "zmin"` on a 3D
grid, `face_coords: ["i", "j"]`."

§8.A.3 step 2: the spatial coord args "follow in declaration order of `side`'s reduced
dimensions." That's the loader's declaration order, which may not match `face_coords`'
declaration order. If they differ, what's normative?

**Fix:** state that `face_coords` is the authoritative ordering and that the loader
reduction-axis order must match it.

### m5. `applies_to` listed as "shallow AST pattern" with no bound on shallowness (§7.1 line 631)

"A **shallow** AST pattern" — how shallow? One op deep? Arbitrary depth? The §7 example has
`{op:"grad", args:["$u"], dim:"$x"}` which is depth-1. §7.3's example has `{op:"div",
args:["$F"], dim:"cell"}` also depth-1. But nothing in the RFC forbids a scheme author from
writing `{op:"D", args:[{op:"grad", args:["$u"]}], ...}`.

**Fix:** either remove "shallow" or pin it to depth-1.

### m6. §11 Step 4 wraps cross-grid indices in `regrid` but doesn't say where the wrap happens (lines 957–959)

"Cross-grid references are wrapped with `regrid`". By the coupling resolver? By the rule
engine at Step 5? By a separate post-coupling pass? If rules can introduce cross-grid
references (e.g. via `produces: ghost_var`), Step 5 also needs to emit `regrid` wrappers.

**Fix:** state "the rule engine must wrap any cross-grid `index` expression it emits in a
`regrid`, and the coupling resolver is responsible for wrapping cross-grid references
produced by `coupling.<c>`. Method selection is handled per M1."

### m7. `max_passes = 32` default is unjustified (line 240)

32 is a magic constant. Why not 8, 16, 64? What's the pathology at 33 that isn't a pathology
at 32? Not a blocker, but cheap to motivate in one line.

**Fix:** one sentence: "chosen as 2× the depth of the deepest MVP-scheme chain" or similar.

### m8. `discretized: true` boolean on output model is load-bearing but under-documented (line 979)

Only one sentence in §11 Step 8. Where does this field live? On the top-level spec? On the
`models.<M>` entry? What does a binding do if it sees `discretized: false` with a
`boundary_conditions` section containing arrayed-index expressions? Reject? Warn? Proceed?

**Fix:** one paragraph under §10.2 or §11 Step 8 describing the field's placement,
validator responsibility, and interaction with loader.

---

## Cross-check against v1 review

I read `docs/rfcs/discretization-review.md` only after writing the above. Summary:

### v1 critical issues — resolution status

| v1 issue | v1 claim | My independent finding | Resolved by v2? |
|---|---|---|---|
| **C1** (`idx` vs `index`) | The RFC v1 added `idx` op that duplicated `index` | v2 §5.1 explicitly drops `idx` and extends `index` contexts | ✅ Resolved. I also flagged the `bare string outside arrayop → parameter` rule as too strict (my M3). |
| **C2** (duplicate BC section) | Both `domains` and `models` had BC sections | §9 promotes to model-level and §16 describes migration | ✅ Resolved. |
| **C3** (canonical form missing) | No normative canonical form; bit-identity unreachable | §5.4 added canonical form | ⚠️ Partially resolved. My C1 shows the canonical form doesn't cover float formatting; my M6 shows `-`, `/`, unary `neg` are unspecified. The *intent* is resolved, the *spec* is not. |
| **C4** (metric loader spec incompatible with §8) | `{kind, name, params}` shape didn't work with existing §8 loader keying | §8.A adds `kind: "mesh"` inline; metric arrays use existing `{loader, field}` pattern | ✅ Resolved. |
| **C5** (pattern-match semantics underspecified) | Binding classes, non-linearity, AC-matching all unspecified | §5.2.1–.5 fills in | ⚠️ Largely resolved. My C4 shows scheme `applies_to` vs. rule `pattern` interaction is still underspecified; my C5 shows termination rule is ambiguous about post-rewrite walk. |

### v1 major issues — resolution status

| v1 issue | My independent finding | Resolved? |
|---|---|---|
| **M1** (scalar dx vs dx[i]) | v2 §6.2.1 adds auto-rewrite for nonuniform spacing | ✅ The nonuniform case. But my M5 shows a different x-vs-y axis problem that's orthogonal and unresolved. |
| **M2** (MPAS variable-valence) | v2 §4 + §7.3 add `reduction` selector and worked example | ⚠️ Structurally resolved, but my C2 shows §7.3 contradicts §7.1.1 on `$target`. |
| **M3** (`$e` target binding) | v2 §7.1.1 pins `$target` components | ⚠️ See C2 — the table itself has a bug. |
| **M4** (axis_flip group action) | v2 §6.4.1 enumerates D₄ action | ✅ Resolved cleanly. Good fix. |
| **M5** (time-dependent loader BCs) | v2 §8.A.3 covers it | ⚠️ Mostly resolved. My M3 shows it contradicts §5.1's parameter-reference rule. |
| **M6** (arrayed variables have no schema) | v2 §10.2 adds `shape`/`location` | ✅ Resolved. |
| **M7** (PR #531 moving target) | v2 §13.1 Step 1b captures fixtures | ✅ Resolved. |
| **M8** (rollout skipped infrastructure) | v2 rewrites §13.1 with Step 1 infra | ⚠️ Resolved in intent. My M8 shows non-Julia/Rust bindings still get ambiguous disposition in Steps 2–4. |

### v1 minor issues

All appear to be addressed (§6.1 advisory note, §6.4.2 panel example, `dim_is_spatial_dim_of`
rename, §11 Step 2 spatialization, §14 risk catalog). Minor issues I flagged above (m1–m8)
are new.

### v1 review questions — resolution

- **Q1** (nested scheme determinism): §5.2.5 pins first-match-wins. Adequate.
- **Q2** (schema-validation reach): §16 enumerates JSON-schema additions. Adequate.
- **Q3** (rule miss behavior): §11 Step 7 errors by default with `passthrough` opt-out. Clean.
- **Q4** (output caching): §14 risk 5 pins per-session. Adequate.
- **Q5** (DAE interop): §12 pins contract. See my M8 — still gap for non-Julia/Rust Steps 2+.
- **Q6** (coupling × rewrite): §11 Step 4 runs coupling before rewrite. See my m6.

---

## New issues introduced by v2

These are genuinely new — they did not exist in v1 because v1 didn't have the feature, or
they were introduced by the v2 revision:

- **C1** (float serialization) — v2 added bit-identity claim and canonical form but not float
  format. v1 had no canonical form so this gap didn't exist in v1's shape.
- **C4** (scheme `applies_to` vs. rule `pattern`) — v2 refined both; v1's `applies_to` was
  less load-bearing.
- **M1** (`regrid.method` unconstrained) — v2 introduced `regrid` op.
- **M2** (periodic BC) — v2 moved BCs to model-level; periodic handling is new territory.
- **M6** (`-`, `/`, `neg` canonicalization) — v2 introduced canonical form.
- **m1** (quadratic canonicalization comparator) — v2 introduced canonical form.
- **m2** (`panel_connectivity` not in §5.1 validator) — v2 tightened the validator.
- **m3** (`+(0,0)` zero-elim order) — v2 introduced canonical form.

Other new spec text (§8.A mesh loader, §12 DAE contract, §9.3 `flux_contrib`) appears
internally consistent and well-motivated; I found no new issues there beyond what's
already listed.

---

## Recommendation

**Targeted fixes needed. Do not proceed to Step 1 on current text.**

Step 1's acceptance is "all five bindings produce byte-identical canonical form on infra
fixtures." C1 alone makes that infeasible; C2 and C3 introduce cross-binding divergence
even before a float appears. These three plus C4 and C5 are spec-level holes that targeted
edits can close without a v3 rewrite. The Major issues are less urgent but need to land
before Step 2–4 fixtures are authored.

**Minimum fix list (to land on v2-final before Step 1 begins):**

1. §5.4.6 — normative number-formatting rule (fixes C1). This is the hardest one; propose
   [RFC 8785 JCS](https://datatracker.ietf.org/doc/html/rfc8785) number format or pin to
   Rust `ryu`-style shortest round-trip with explicit rules for integer-valued floats.
2. §7.1.1 — "choose `$target` scalar by `emits_location` if set, else by operand's
   `location`" (fixes C2).
3. §7.2 — one sentence on dim-name → `$target` component mapping (fixes C3).
4. §7.1 / new §7.2.1 — pin scheme-`applies_to` vs. rule-`pattern` protocol (fixes C4).
5. §5.2.5 — pick option (a) for post-rewrite walker behavior (fixes C5).
6. §5.3 / §7.2 — pin where `regrid.method` is sourced (fixes M1).
7. §9.2.1 — new sub-section on periodic BCs with a worked example (fixes M2).
8. §5.1 — extend "bare string" resolution to include BC `face_coords` and model
   `independent_variable` (fixes M3).
9. §7.1 — state that a scheme is axis-specific OR add axis-parameterized metric lookup
   (fixes M5).
10. §5.4 — canonicalization rules for `-`, `/`, unary negation (fixes M6).

The minors (m1–m8) can roll in as editorial clean-up.

After these fixes, v2 is ready for Step 1. The architectural direction is right; the
three-selector unification, the MPAS reduction selector, and the model-level BC promotion
are all on solid ground.

---

*End of parallel review.*
