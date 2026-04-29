# Expression Templates Conformance Fixtures (esm-spec §9.6)

These fixtures exercise the `expression_templates` block and the
`apply_expression_template` AST op landed in v0.4.0 (RFC
`docs/content/rfcs/ast-expression-templates.md`, bead esm-giy).

## Fixtures

### `arrhenius_smoke/fixture.esm`

A reaction system declaring a 2-parameter `arrhenius` template
(`A · exp(-Ea / T) · num_density`) and three reactions whose rates use it
with different scalar bindings. After load-time expansion (Option A
round-trip; esm-spec §9.6.4 rule 1), every `apply_expression_template`
node MUST be replaced by the structurally-identical inline AST that
authoring the same form by hand would produce. All five bindings (Julia,
TypeScript, Python, Rust, Go) must agree on the post-expansion AST
byte-for-byte after canonical serialization.

### `arrhenius_smoke/expanded.esm`

The expected post-expansion form of `arrhenius_smoke/fixture.esm` —
i.e. what `load(fixture.esm)` then re-serialize MUST emit
(Option A round-trip is "always-expanded": the canonical AST after parse-then-emit
is the expanded form, never the source). Conformance harnesses load the
template fixture, re-serialize, and assert structural equality with this file.
