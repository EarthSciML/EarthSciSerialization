# Critical Review v2 — RFC: Language-agnostic Discretization in ESM

**Reviewer:** brahmin (polecat, independent of v1 reviewer)
**Reviewing:** [`docs/rfcs/discretization.md`](discretization.md) (1386 lines, v2 via gt-yx9y)
**Against:** [`docs/rfcs/discretization-review.md`](discretization-review.md) (v1 review, gt-tlw2)
**Bead:** gt-j6do
**Date:** 2026-04-18

## Summary

V2 makes real progress. The `idx`/`index` collision (C1), the BC duplication
(C2), the MPAS variable-valence gap (M2), the MPAS-loader addressing
inconsistency (C4), the D₄ action (M4), the missing arrayed-variable schema
(M6), and the rollout restructure (M8) are all genuinely addressed — not
merely gestured at. However, v2 still does **not** deliver the bit-identity
guarantee its §12/§13 continue to advertise, because (a) §5.4's canonical
form omits three hazards explicitly called out in the review brief
(float subnormals, NaN/Inf, JSON number serialization), and (b) §7.3's
lowering produces an `arrayop` that does **not conform to the base spec's
§4.3.1 `arrayop` schema** — the RFC invents new fields (`idx`, `{lo,hi}`
ranges, object-shaped `reduce`) where the base spec mandates `output_idx`,
`[start, stop]` pair ranges, and a string `reduce`. Until that is fixed,
Step 3's "lowers to `arrayop`, consistent with §4" claim is false. Three
smaller but load-bearing definitional gaps (undefined `region` field,
`produces` absent from §5.2's rule-field table, `apply_axis_flip`
illustrative-but-also-shown-as-an-op in §6.4.2) compound the arrayop
problem. **Recommendation: targeted v3. Spec is close — not ready for
Step 1.**

## Per-issue verification (v1 findings against v2 claims in §17)

Each row: v1 issue → v2's cited resolution → independent verdict (section
cites refer to `discretization.md`).

### Critical issues

| v1 | v2 cites | Verdict | Notes |
|---|---|---|---|
| **C1** `idx` vs `index` | §5.1 | **Resolved** | `idx` dropped (L148). `index` contexts extended (L120–138). §5.1.3 adds reduction rules for `makearray`, `broadcast`, `reshape/transpose/concat` operands. |
| **C2** BC duplication | §9, §10.1, §16.1 | **Resolved** | Breaking removal of `domains.<d>.boundary_conditions` documented (L905, L916), migration rule in §16.1 is concrete and mechanically applicable (L1268–1277). |
| **C3** canonical form missing | §5.4 | **Partially resolved** | Ordering, flattening, identity-elim, and a worked example are normatively specified (L304–369). Three hazards the review brief specifically called out are **not** covered — see **New C1** below. The cross-binding bit-identity claim is therefore not yet defensible. |
| **C4** metric loader refs nonexistent extension | §8.A | **Partially resolved** | Addressing now uses existing `data_loaders` key + field (L792, L794–797). BUT `mesh` loaders now expose fields through **three** parallel paths (`connectivity_fields`, `metric_fields`, plus §8.A.3's existing `variables.<schema_name>` for time-dependent fields, L806). Addressing is consistent within each; it is not consistent **across** the three paths. See **New M1**. |
| **C5** pattern-match semantics | §5.2.1–§5.2.6 | **Partially resolved** | Binding classes (L167–191), non-linear patterns (L194–199), AC rejection (L201–212), termination rule (i) with pass budget of 32 (L232–243) are all pinned. The one-page worked example (L246–285) is exactly what the v1 review asked for. Remaining gap: the **leaf-vs-subtree** disambiguation for `$u` in `grad`/`div`/`laplacian`'s `args[0]` is left to the guard. See **New M3**. |

### Major issues

| v1 | v2 cites | Verdict | Notes |
|---|---|---|---|
| **M1** scalar `dx` vs indexed | §6.2.1 | **Resolved** | Engine auto-rewrites at expansion time (L447–461); bit-identity preserved because all bindings apply at the same pipeline point. |
| **M2** MPAS variable-valence | §4, §7.3 | **Broken by arrayop-schema mismatch** | The `reduction` selector is well-motivated (L102–106, §4), but §7.3's lowered output is **not a valid base-spec `arrayop`** — see **New C2**. The architectural claim is right; the concrete lowering is wrong. |
| **M3** `$e` target binding | §7.1.1 | **Partially resolved** | `$target` components per family listed (L650–654). "Component names are reserved keywords" (L656) but cartesian is only shown as `[i, j, k, ...]`; the spec does not say what the 4th and 5th component names are for ≥4D grids, nor how a scheme author references them. See **New m1**. |
| **M4** `axis_flip` D₄ action | §6.4.1 | **Resolved** | Full 8-row table with rotations and reflections (L529–539). Conformance is unambiguous. |
| **M5** time-dependent BCs | §8.A.3 | **Partially resolved** | `t` is explicit (L810–812), `face_coords` declared on the BC entry (L869). BUT the spec does not say whether the loader field is typed (grid-valued? scalar-valued at each face?) or whether the runtime handle must honor the `determinism` block (§8.A) for the time-varying field. See **New M4**. |
| **M6** arrayed-variable schema | §10.2 | **Resolved** | `shape` and `location` added inline (L929–938). Default rules pinned (L918–920). |
| **M7** PR #531 moving target | §13 Step 1b | **Resolved** | Fixtures captured "at commit SHA pinned in the fixture header" (L1055–1058). Upstream drift is explicitly non-invalidating. |
| **M8** rollout skipped infrastructure | §13 | **Resolved** | Step 1 is now pure infrastructure (L1017–1045); scheme work moves to Step 1b onwards. This is the right structure. But Step 1 *acceptance* (L1039–1045) tests only parse/canonicalize/serialize — not the rule engine, canonical form, or migration tool that Step 1 *scope* (L1018–1036) promises. See **New M2**. |

### Minor issues

| v1 | v2 cites | Verdict |
|---|---|---|
| **m1** `grid_spacing` duplication | §6.1 | **Resolved** (L409–413; advisory, future-deprecate). |
| **m2** panel selector example | §6.4.2 | **Resolved** (L553–569; worked with seam case). |
| **m3** analytic cube metric placeholder | §6.4 | **Resolved** (L509–513; concrete `atan2`/`cos` expression). |
| **m4** guard name inconsistency | §5.2.4 | **Resolved** (renamed to `dim_is_spatial_dim_of`, L220). |
| **m5** spatialization responsibility | §11 step 2 | **Resolved** (L949–952). |
| **m6** closed vocabulary risks | §14 risk 1 | **Resolved** (L1114–1121, listed and labeled out-of-MVP). |
| **m7** CSV loader by name | §13 Step 2 | **Resolved** (L1357–1359, loader name is authored, not reserved). |
| **m8** two-stage matching | §7.1 | **Partially resolved** — §17's L1361 says "a rule fires first; a scheme's `applies_to` is matched at expansion time". But §7.1 itself does not contain this statement; it is only in §17's review-response prose. It belongs in normative text (§7.1 or §7.2). |
| **m9** `produces: state_var` | §9.4 | **Resolved** (removed from MVP, L898–899). |

### Review questions

| v1 | v2 cites | Verdict |
|---|---|---|
| **Q1** nested scheme determinism | §5.2.5 | **Resolved** (rule (i): rewritten subtree not re-matched in pass). |
| **Q2** schema-validation reach | §16 | **Partially resolved** — §16 lists the schema additions but does not distinguish JSON-Schema-encodable vs loader-enforced (e.g., rule-cycle detection, grid/scheme compatibility must be loader-side; pattern-variable scoping is mixed). The review question asked for the distinction; v2 does not draw it. |
| **Q3** rule-miss behavior | §11 step 7 | **Resolved** (`E_UNREWRITTEN_PDE_OP` with `passthrough` opt-in, L964–971). |
| **Q4** output caching | §14 risk 5 | **Resolved** (per-session, per-binding, L1133–1135). |
| **Q5** DAE interop assumption | §12 | **Partially resolved** — prose is clear (L981–997) but the *conformance test* that verifies non-DAE bindings error rather than silently drop constraints is missing. See **New M5**. |
| **Q6** coupling × rewrite | §11 step 4, §5.3 | **Resolved** (L957–959: post-coupling rewrite, `regrid` wraps cross-grid). |

## New critical issues (introduced by v2 or still unresolved)

### New C1. Canonical form misses the three hazards the review brief flagged

The task prompt explicitly asked whether §5.4 covers: **(a) float subnormals,
(b) NaN/Inf, (c) equivalent-but-not-equal representations including `0 * x`,
(d) mixed-arity chains**.

- **(a) Subnormals.** Not addressed. §5.4.1 says integer and float literals
  are distinct nodes, but there is no rule for how `1e-310` is serialized.
  JSON number serialization is language-defined: Go's `strconv.FormatFloat`,
  Rust's `ryu`, Julia's default, Python's `repr` all agree on most values
  but diverge on subnormals and on the shortest-roundtrip string for values
  near `±0.0`. §5.4's byte-comparison strategy (L322, L367–368) is not
  byte-stable across bindings without a pinned JSON number serialization
  (e.g., RFC 8785 JCS). **Not pinned.**
- **(b) NaN/Inf.** Not addressed. These are not JSON numbers at all; each
  binding will spell them differently (`null`, `"NaN"`, `"Infinity"`,
  `{"op":"special","name":"nan"}` are all plausible). The RFC does not say
  whether a canonical AST may contain NaN/Inf or how.
- **(c) Zero/identity with mixed types.** §5.4.4 says `*(0, ...) → 0` and
  `*(1, x, ...) → *(x, ...)`. But §5.4.1 says integer and float literals
  are distinct nodes and "promotion happens only in `evaluate`". So: does
  `*(1.0, x)` canonicalize to `x` (losing the float-ness) or to `*(1.0, x)`
  (keeping it)? L345–347 picks the first: "`*(1.0, x)` is `x`, and the
  resulting expression has no type tag — type is inferred from the
  surviving operand." This **contradicts** §5.4.1's non-promotion rule:
  multiplying by `1.0` produces a float in every evaluation semantics, but
  the canonical form has dropped that information. A rule that strips type
  is a promotion rule. Two bindings whose evaluation honors `1.0 * int =
  float` will nonetheless emit `x` (int) after canonicalization and then
  evaluate `x` (int) — wrong answer, but bit-identical. The fix is either
  (i) disallow identity elim across int/float, or (ii) declare the output
  of `*(1.0, x)` is `*(1.0, x)` (no elim when the operand types differ).
  Neither is pinned.
- **(d) Signed zero.** `-0.0` vs `+0.0`. §5.4 says nothing. `*(x, 0)`
  → `0` erases sign. For subsequent use in `/` this matters.
- **(e) JSON number string form.** As above: §5.4's byte-comparison
  presumes a canonical number spelling that is not specified. **This is
  the single largest risk to the §12 bit-identity claim.**

The review brief specifically called these out as "the cases not covered"
where "two bindings will diverge." v2 does not close them.

**Verdict:** §13's "Julia + Rust emit bit-identical canonical AST"
acceptance is not yet decidable on numeric-literal corner cases. Either
normatively adopt RFC 8785 JCS (or an equivalent) for number spelling and
explicitly list subnormal/NaN/Inf/signed-zero rules, or weaken the §12
claim to "algebraic equivalence on a seed set."

### New C2. §7.3's lowered `arrayop` does not conform to base-spec §4.3.1

§7.3 is the MPAS worked example that backs the M2 resolution. Its lowered
form (L722–734) uses:

```json
{ "op": "arrayop",
  "idx": ["k"],
  "ranges": { "k": { "lo": 0, "hi": {...} } },
  "reduce": { "op": "+", "init": 0 },
  "expr": ... }
```

But `esm-spec.md` §4.3.1 (verified against `esm-spec.md` L179–230)
mandates:

- `output_idx`, not `idx` (`esm-spec.md` L180, L199, L225).
- Ranges with `[start, stop]` integer pairs, not `{lo, hi}` objects
  (`esm-spec.md` L210–213, L239).
- `reduce` as a string op (`"+"`) — the existing example at `esm-spec.md`
  L227 uses `"reduce": "+"`, a bare string. The RFC's `{"op": "+", "init":
  0}` object form is new.
- An `args` field listing the arrays referenced (`esm-spec.md` L241).
  §7.3's lowered form has no `args`.

The RFC nowhere amends §4.3.1 to admit these field shapes. §16 (Deliverable
checklist, L1239–1253) does not list an `arrayop` amendment. So either:

(a) the lowered form is a typo and should be rewritten to match base-spec
`arrayop` (in which case §7.3 needs re-authoring), or

(b) the RFC is silently shipping a second `arrayop` dialect alongside the
first — which is exactly the kind of parallel-mechanism problem C1 was
designed to prevent.

This is a **new critical issue**: the foundational claim that MPAS lowers
to the existing `arrayop` template (§4 L68, §7.3 L741–744) is false as
written. Step 3 is unverifiable until §7.3 produces a valid `arrayop`.

Fix: rewrite §7.3's lowered JSON using `output_idx: []` (empty — the result
is a scalar at cell `c`), `ranges: {"k": [0, <expr>]}`, `reduce: "+"`,
`args: ["F", "dvEdge", "areaCell", "edgesOnCell"]`. Verify the lowered
expression is legal against the JSON schema, not just plausible.

## New major issues

### New M1. `mesh` loader's three parallel field-addressing paths

§8.A now exposes fields from a single mesh loader through three disjoint
lists:

1. `mesh.connectivity_fields` (L763) — for integer connectivity.
2. `mesh.metric_fields` (L764) — for float metrics.
3. `variables.<schema_name>` — existing §8.5 (cited at L806) for
   time-varying fields referenced by BCs.

The distinctions are not mechanical: a hypothetical `cellMask` integer
field is connectivity-like; a hypothetical `cellElevation` time-invariant
float is metric-like; a `cellSurfaceTemperature` time-varying float must
go to `variables.<name>`. But the partitioning is by *intent*, not by
type — no validator can decide. The spec offers no guidance for:

- A field that is time-varying **and** mesh-dependent (e.g., an observed
  SST that is defined only at sea cells). Does it go to
  `variables.<name>` or `metric_fields`?
- A loader that authors use for **both** connectivity and BC value.
  Which list wins?

**Recommendation:** collapse `connectivity_fields` and `metric_fields`
into a single `mesh_fields` list with per-entry `{type: "int"|"float",
semantic: "connectivity"|"metric"|"value"}`, so the partitioning is
data-driven. Or state that time-varying fields go only to
`variables.<name>` and mesh fields are time-invariant by construction.

### New M2. Step 1 acceptance does not exercise Step 1 scope

Step 1 scope (L1018–1036) lists: rule engine, canonical form, `regrid` op,
arrayed-variable schema, BC section, `passthrough`, `max_passes`,
migration tooling.

Step 1 acceptance (L1039–1045) is:

> - All five bindings parse, canonicalize, and serialize every fixture in
>   `tests/conformance/discretization/infra/` to the byte-identical
>   canonical form.
> - `esm migrate` on the three schema-migration fixtures produces
>   expected output.
> - No `rules` / `discretizations` / `grids` section is exercised yet.

"Parse, canonicalize, serialize" tests the loader and the canonicalizer.
It does **not** test the rule engine, `regrid` expansion, or `passthrough`
behavior. Step 1 ships infrastructure that Step 1b depends on, but Step 1
does not verify that infrastructure works. A failing rule engine in all
five bindings would pass Step 1 acceptance and break Step 1b.

**Recommendation:** Step 1 acceptance must include at least one fixture
that invokes the rule engine (a trivial pattern that produces a known
output), `regrid` ⇒ canonical form, and a `passthrough: true` pre-tagged
equation that the engine leaves alone. Without that, "Step 1 done" is
not a meaningful gate.

### New M3. `grad`/`div`/`laplacian` `args[0]` leaf-vs-subtree

§5.2.1 (L170–178) declares three binding classes: name, leaf, subtree.
The per-op table (L182–191) lists which sibling fields are name-class. It
does **not** list which `args` positions are leaf-class. The rule is:
"An `args` position whose surrounding op **requires** a bare name."

What ops require a bare name in `args[0]`?

- `D`: yes per spec convention, but not stated in §5.2.1.
- `grad`/`div`/`laplacian`: spec examples (`esm-spec.md` L848, L852) all
  use bare strings, but the spec does not mandate them. Per the existing
  spec, any Expression is permitted.

So `{op:"grad", args:["$u"], dim:"$x"}` has two plausible readings:

(i) `$u` is leaf-class — matches only bare variable names. Then
    `{op:"grad", args:[{op:"*", args:["rho","u"]}]}` doesn't match.
(ii) `$u` is subtree-class — matches anything, and the guard
    `var_has_grid` fails silently (or errors) when `$u` is not a name.

The binding class is determined by the pattern's *position*, not the
instance tree, per L169. So without a per-op leaf vs. subtree table for
`args` positions, two bindings will pick different readings. The v1
review's C5.1 asked exactly this; v2 declares the principle (§5.2.1) but
does not enumerate the table that makes it actionable.

**Recommendation:** add a per-op `args`-position table similar to the
sibling-field table at L182–191, stating for each op whether `args[0]`,
`args[1]`, … bind leaf-class or subtree-class. For `grad`/`div`/`D`/
`laplacian`, leaf-class is correct.

### New M4. Loader `determinism` block does not cover time-varying fields

§8.A's `determinism` block (L767–771) covers `endian`, `float_format`,
`integer_width` for the *file* the loader reads. But §8.A.3's time-varying
fields (used in BCs, L806–808) are not file-resident — they come from the
runtime loader's callable output at each time `t`. The `determinism` block
has no clause for the runtime interpolation or the temporal resampling
algorithm.

Two bindings receiving the same `.esm` and the same loader binary can
still produce different BC values at time `t=0.5` if one binding uses
linear interpolation and the other uses nearest-neighbor. The RFC does
not say which the `kind: "mesh"` or `kind: "grid"` loader must use.

**Recommendation:** extend `determinism` with a `temporal_interpolation`
field (closed enum: `"nearest"`, `"linear"`, `"step_left"`, `"step_right"`)
and make it required for time-varying fields.

### New M5. §12 has no conformance test for "abort with E_NO_DAE_SUPPORT"

§12 (L984–993) is clear about the binding contract: "must either (a) hand
to DAE assembler, or (b) abort with error code `E_NO_DAE_SUPPORT`." It
states that silent omission or demotion is non-conforming.

But §13 rollout's acceptance criteria (L1037–1110) test only bit-identity
and solver parity. No step tests that a non-DAE-capable binding errors out
rather than silently dropping an algebraic constraint. For a spec claim
that "silent omission is non-conforming," there must be a fixture that
reveals silent omission.

**Recommendation:** Step 2 or Step 3 (both introduce `produces: algebraic`
rules) must add a fixture that expects `E_NO_DAE_SUPPORT` from a binding
that has been configured to disable DAE support. The fixture lives in
`tests/conformance/discretization/dae-missing/` and asserts the error
code is returned; silent success is a test failure.

### New M6. Arrayed `shape` + cross-model `coupling.transforms` not reconciled

§10.2 adds `shape` to `variables.<name>`. §10 (L911) says coupling is
"unchanged." But the existing coupling `variable_map.transforms` operates
on continuous scalar variables (per `esm-spec.md` §10.4). After Step 2,
those variables may carry `shape`. What happens when:

1. Model A's variable `u` has `shape: ["x", "y"]` (2D); model B's `v`
   has `shape: ["x", "y", "z"]` (3D).
2. A coupling `variable_map` with a `translate` transform maps `u` to
   `v` (replacing a parameter in B with A's `u`).

§11 step 4 says couplings are applied *before* rewrite on continuous
variables. But by the time Step 2 runs the discretization pipeline, `u`
already has a `shape`. Either coupling happens on the continuous scalars
(before shape-tagging, §11 step 2), in which case the shapes never meet
— but step 2 runs before step 4 (location tagging is step 2, coupling is
step 4). So shapes are assigned first, then coupling runs on shaped
variables, with no reconciliation rule.

**Recommendation:** clarify in §10 (coupling row) what `variable_map`
does when source/target have different `shape`. Options: error,
implicit `regrid`, or forbid shape-mismatched couplings without an
interface. Any of the three is defensible; none is in v2.

## New minor issues

### new-m1. `$target` components for ≥4D cartesian grids are undefined

§7.1.1 (L652) gives cartesian `$target` as `[i, j, k, ...]`. The `...`
elides. If a cartesian grid has 4 dimensions (e.g., `[x, y, z, w]`), what
is the 4th `$target` component? `l`? `i_4`? If an author writes `"w"` as
a dimension name, the reserved-keyword clause (L656) is silent on which
4th letter is reserved. In practice few grids exceed 3D, but the spec
should either say "at most 3 dimensions for cartesian in v0.2" or
enumerate the letter mapping for higher dimensions.

### new-m2. `"region": "interior"` in §5.2.6 worked example is undefined

L256 uses a `region` field in the rule object. `region` is not defined
anywhere else in the RFC — not in §5.2 (rule fields table, L158–161),
not in §7 (discretization fields), not in §16 (schema deliverable).
Either it is authored ESM-meta data (then define what it does and
enumerate values), or it is vestigial from v1 and should be deleted from
the example. Leaving it in the worked example is a spec bug: a reader
writing a conforming rule will not know whether `region` is required,
optional, ignored, or reserved.

### new-m3. `produces` is missing from §5.2's rule-field table

§5.2 (L158–161) lists rule fields: `pattern`, `where`, `replacement`.
But §9.4 (L889) says "A rule may emit additional equations via
`produces[k]`", and §11 step 5 (L962) consumes `rules[*].produces`. So
`produces` is a fourth rule field. It belongs in the §5.2 table with
its type (array of `{kind, emit|value}` objects) and semantics
cross-referenced to §9.4.

### new-m4. `"use"` vs `"replacement"` are alternatives; only `"use"` is shown

§5.2 (L161) documents that `replacement` "(or `use:<scheme>`)" is legal.
The §5.2.6 worked example (L255) uses `use`, not `replacement`. But
there is no second worked example showing `replacement` in its inline
AST form. A reader will reasonably infer `use` is *the* canonical form
and `replacement` is a synonym — the intent is the opposite. Add a
second tiny example that uses `replacement` directly.

### new-m5. `apply_axis_flip` is illustrated as an `op` but claimed not to be one

§6.4.2 (L565–566) shows `{"op": "apply_axis_flip", ...}` in the worked
example. The footnote (L571–576) says `apply_axis_flip` is **not** an
AST op, "it is an alias for the table lookup in §6.4.1 [...] The
`apply_axis_flip` spelling above is illustrative; the materialized form
is deterministic per §6.4.1's enumerated table."

A worked example in a normative spec should show the actual on-wire
form, not a pedagogical stand-in. A binding implementer reading §6.4.2
will reasonably try to implement `apply_axis_flip` as an AST op and
then struggle with a schema validator that doesn't recognize it.

**Recommendation:** replace L565–566 with the piecewise-expanded form
(the 8-case switch from the D₄ action table), even though it is longer.
Or move §6.4.2 to a separate appendix explicitly labeled "illustrative
pseudocode — not canonical on-wire form".

### new-m6. Scheme `applies_to` matching is explained only in §17

§17's review response for m8 (L1360–1363) says:

> Clarified in §7.1: a rule fires first; a scheme's `applies_to` is
> matched against the rule's `$u` / `$target` binding at expansion time.
> There is no second pass of rule matching against `applies_to`.

But §7.1 itself (L629–661) does not contain this statement. The pipeline
ordering (rule → scheme expansion, not rule-and-scheme-interleaved) is
load-bearing for determinism; it must be in normative text, not just in
a response-to-review section.

**Recommendation:** add a one-sentence paragraph to §7.1 (or §7.2)
saying: "A scheme's `applies_to` is matched against the bound
`$target`/pattern-variable values at expansion time; the rule engine
(§5.2) and scheme expansion (§7.2) are sequential, not interleaved."

### new-m7. `reduction` selector's `k_bound` is a name-class keyword but unlisted

§7.3 uses `"k_bound": "k"` in the `reduction` selector (L704). This is
the name of the iteration variable that the expansion (§7.2 `reduction`
row, L682) binds inside the lowered `arrayop`. Per the §5.2.1
name-class table (L182–191), `reduction` is not listed among ops with
name-class fields. So the binding class of `k_bound`'s value is
unspecified. Add a row to the §5.2.1 table, or move the reduction
selector's inner fields into a dedicated §5.2.1-like enumeration at §4.

### new-m8. `builtin` generator list is closed but not versioned-separately

§6.4.1's `{kind:"builtin", name:...}` generator (L547) declares the
legal `builtin` names: `gnomonic_c6_neighbors`, `gnomonic_c6_d4_action`.
"Adding a value is a minor version bump" is stated for `mesh.topology`
(L783) but not for `builtin.name`. If the spec ships 0.2.0 with two
builtins and later a FV-3-specific builtin is added, is that a minor
bump (0.2.x) or major (0.3)? State the policy.

## Questions v2 should answer but doesn't

1. **Number serialization.** What is the normative number spelling? See
   **New C1**. Without this, §13's byte-comparison assertion is undefined
   on any fixture that contains float literals.

2. **Interior vs. boundary region separation.** The `region: "interior"`
   at L256 hints at a region-based rule-dispatch model. Does the spec
   support `region: "xmin_boundary"` or similar? If yes, where is that
   specified? If no, why does the worked example use it?

3. **`regrid` method determinism.** §5.3 L301–303 says `method` is a
   bare string, not schema-validated. But §13's bit-identity claim
   requires that Julia and Rust agree on what `"bilinear"` does. Either
   pin a set of method names with normative semantics, or weaken the §13
   claim for expressions containing `regrid`.

4. **Rule conflict when two rules match the same subtree.** §14 risk 2
   says "the first-listed rule wins." But rules live under `rules` which
   §3 (L56–60) treats as a map (keyed by name), not an array. Map key
   order is not language-deterministic in JSON. So "first-listed rule"
   requires either an array (not a map) under `rules`, or a `priority`
   integer field. Clarify.

5. **Ghost-cell naming collisions.** §9.4's `produces: ghost_var`
   declares a new variable. Two schemes emitting `ghost_u_xmin` collide.
   What's the naming discipline? Scheme-scoped? Model-scoped? Globally
   unique by `<scheme>.<var>.<side>` convention?

6. **`spec.canonical_form_applied: true` opt-in.** §5.4 (L307–309)
   allows a loader to skip canonicalization when this flag is set.
   What guarantees a loader that sees `canonical_form_applied: true`
   actually has the input in canonical form? A malicious or buggy
   upstream can lie. Recommend: always canonicalize, ignore the flag.

## Final recommendation: **v2 needs targeted fixes (v3 required)**

V2 is much stronger than v1 — the review response section §17 is honest
and the critical issues C1, C2, C4 (addressing part), C5, M2, M4, M6,
M7, M8, and most minors are genuinely resolved. The design is close to
Step-1-ready. **Three targeted fixes are blocking**:

1. **Fix the `arrayop` schema mismatch in §7.3** (**New C2**). This is a
   mechanical fix: rewrite the JSON to use `output_idx`/`[start, stop]`
   ranges/string `reduce`/`args`. Should be < 1 hour of work.

2. **Close the canonical form's numeric-literal hazards** (**New C1**).
   Adopt RFC 8785 JCS normatively for number spelling; list explicit
   rules for NaN/Inf/subnormals/signed zero; resolve the `*(1.0, x)` →
   `x` vs no-elim conflict. Needed before any Step's bit-identity claim
   is decidable.

3. **Add rule-engine exercise to Step 1 acceptance** (**New M2**).
   Step 1 ships infrastructure; acceptance must verify the
   infrastructure runs, not just that JSON round-trips.

The remaining new-major and new-minor items (New M1, M3–M6; new-m1
through new-m8) are secondary and can land incrementally in Step 1b or
later.

**Do not open Step 1 against v2 as written.** The three blockers above
are small; a v3 addressing them should be quick. A reviewer asked to
sign off on bit-identity across bindings on v2 cannot, because (a) the
canonical form has open gaps and (b) the worked MPAS lowering itself
does not parse as a valid base-spec `arrayop`.

---

*End of v2 review.*
