//! Build-time value-equality (`join.on`) resolution for `aggregate` /
//! `arrayop` nodes — the M2 core of RFC `semiring-faq-unified-ir` §5.3, under
//! the cross-binding determinism contract of §5.7 / `CONFORMANCE_SPEC.md` §5.5.
//!
//! `join.on` adds combination of factors by **value equality of key columns**
//! (an inner equi-join), subsuming ESI `join` and making connectivity gathers
//! first-class instead of a positional einsum on a shared index. The relational
//! semantics are fixed, not implementation-defined (§5.3):
//!
//! - **Inner only.** A combined ⊗-product term exists only for index
//!   combinations whose key columns are equal on *every* listed pair. An
//!   unmatched row contributes nothing — the additive identity `0̄` (§5.1) — so
//!   it adds zero to a `sum_product` aggregate and leaves a `min_sum` at `+∞`.
//! - **Many-to-many is defined.** A key occurring `m` times left and `n` times
//!   right yields all `m·n` combined tuples, each one ⊗-term into the enclosing
//!   ⊕-reduction. This is categorical disaggregation (ESI), specified — not an
//!   error to guard against.
//! - **Exact-equality keys only.** Keys are integer IDs or categorical members
//!   (strings compared by Unicode code point). **Floats are forbidden in keys**
//!   ([`JoinKey::from_json`] rejects them), for the same reason floats are
//!   forbidden in Skolem keys: equality is not portable across bindings.
//! - **Null / missing keys.** A null/absent key column makes a row unmatchable
//!   (it joins to nothing → `0̄`); nulls never compare equal, not even to each
//!   other. Emitting `null` *into* a key column is a build-time error.
//!
//! **Determinism (§5.7 rule 5).** Hashing may bucket only; the emitted result
//! MUST be **sorted by the canonical key**, never hash-iteration / first-seen
//! order. [`inner_equi_join`] buckets the right relation in an [`IndexMap`] and
//! then emits sorted by [`JoinKey`] total order, so the output is independent of
//! input order, duplicates, and orientation. The ⊕ used to combine duplicates is
//! associative + commutative for every registry semiring, so input and parallel
//! order cannot change a reduced value; [`group_by_reduce`] performs each
//! bucket's reduction sequentially in canonical input order so a float ⊕ has no
//! last-ULP drift.
//!
//! **Build-time, same artifact.** Like [`crate::aggregate::resolve_aggregate_ranges`],
//! [`resolve_aggregate_joins`] runs once on an owned model before shape
//! inference. The **degenerate positional case** — a join whose key columns are
//! already the aggregate's declared loop indices (the common dense-categorical
//! disaggregation, §7.2) — needs no runtime matching: the existing dense einsum
//! already combines those factors positionally, so resolution is a structural
//! no-op and evaluation stays byte-identical to the no-join form. A join over
//! key columns that are *not* loop indices would require the runtime
//! value-equality engine over data-derived factor columns (the ragged / derived
//! factor model the dense Rust evaluator does not yet carry — M3); that is
//! rejected with a clear error, mirroring the ragged/derived range handling,
//! rather than silently mis-combined.

use std::collections::HashSet;

use indexmap::IndexMap;
use serde_json::Value;

use crate::aggregate::{ReduceKind, is_aggregate_op};
use crate::simulate::CompileError;
use crate::types::{Expr, ExpressionNode, Model};

/// One component of a join / group-by key. Exact-equality types only (§5.3):
/// an integer ID or a categorical member. **Floats are forbidden in keys**
/// (§5.7 rule 1) — they never reach this enum; [`JoinKey::from_json`] rejects
/// them at the boundary.
///
/// The derived [`Ord`] **is** the normative total order (§5.5.1 rule 1):
/// integers compare by value, strings by Rust `str` order which for valid UTF-8
/// is Unicode code-point order (equivalently UTF-8 byte order), *not* locale
/// collation — so `"B"` (U+0042) < `"Z"` (U+005A) < `"a"` (U+0061), which a
/// case-insensitive locale would wrongly interleave. The variant order pins the
/// cross-type tiebreak (`Int` before `Cat`); in practice a given key column is
/// homogeneous, but a defined total order must still be total.
#[derive(Debug, Clone, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum JoinKey {
    /// An integer index / categorical-by-id key component.
    Int(i64),
    /// A categorical member, compared by Unicode code point (UTF-8 byte order).
    Cat(String),
}

/// Why a JSON value cannot be a join key (§5.3 / §5.7 rule 1).
#[derive(Debug, Clone, PartialEq)]
pub enum KeyError {
    /// A floating-point component — forbidden: equality is not portable across
    /// bindings (a `5.0` repr is platform-dependent). Carries the offending value.
    Float(f64),
    /// A `null` / missing component emitted *into* a key column — a build-time
    /// error (§5.3: not silently dropped).
    Null,
    /// A non-scalar (array / object) component, which cannot be an equality key.
    NonScalar,
}

impl JoinKey {
    /// Project a JSON scalar into a [`JoinKey`], enforcing the §5.7 rule-1 key
    /// type discipline. Integers and strings pass; a JSON `null` is a
    /// build-time error ([`KeyError::Null`]); a genuine float is rejected
    /// ([`KeyError::Float`]) rather than silently bucketed on a
    /// platform-dependent representation. A JSON bool maps to `Int(0/1)` — a
    /// categorical 0/1 id, matching the reference primitives (Python treats
    /// `bool` as an `int` subclass).
    ///
    /// Note a JSON `5.0` (any number carrying a fractional/exponent token) is a
    /// float and is rejected, while `5` is an integer and yields `Int(5)` — the
    /// same integer-vs-float distinction the canonical number tokenizer draws.
    pub fn from_json(v: &Value) -> Result<JoinKey, KeyError> {
        match v {
            Value::Null => Err(KeyError::Null),
            Value::Bool(b) => Ok(JoinKey::Int(i64::from(*b))),
            Value::Number(n) => match n.as_i64() {
                Some(i) => Ok(JoinKey::Int(i)),
                // Not representable as an i64 ⇒ it is a float token (or an
                // out-of-range integer); either way it is not a portable
                // exact-equality key.
                None => Err(KeyError::Float(n.as_f64().unwrap_or(f64::NAN))),
            },
            Value::String(s) => Ok(JoinKey::Cat(s.clone())),
            Value::Array(_) | Value::Object(_) => Err(KeyError::NonScalar),
        }
    }

    /// The JSON scalar form of this key component, for canonical serialization.
    fn to_json(&self) -> Value {
        match self {
            JoinKey::Int(i) => Value::from(*i),
            JoinKey::Cat(s) => Value::from(s.clone()),
        }
    }
}

/// Project a whole key tuple from JSON components, failing on the first
/// component that violates the key-type discipline (§5.7 rule 1).
pub fn key_tuple_from_json(components: &[Value]) -> Result<Vec<JoinKey>, KeyError> {
    components.iter().map(JoinKey::from_json).collect()
}

/// One emitted combined tuple of an [`inner_equi_join`]: the shared key plus
/// the source-row indices on each side. `left`/`right` index back into the
/// relations passed to the join, so the caller can gather the corresponding
/// factor values for the ⊗-product term.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct JoinMatch {
    /// The equal key value both rows carry.
    pub key: Vec<JoinKey>,
    /// Index of the contributing row in the left relation.
    pub left: usize,
    /// Index of the contributing row in the right relation.
    pub right: usize,
}

/// Inner equi-join of two relations by the value equality of their key
/// projections (§5.3). Each entry of `left` / `right` is a row's key tuple, or
/// `None` if a key column is null/missing on that row (which makes the row
/// **unmatchable** — it joins to nothing and contributes `0̄`, §5.3).
///
/// The right relation is bucketed by key in an [`IndexMap`] (hashing used only
/// to bucket); the left relation probes it. Many-to-many is defined: a key with
/// `m` left rows and `n` right rows emits all `m·n` matches (§5.3). The result
/// is then **sorted by the canonical key**, with `(left, right)` as a stable
/// tiebreak, so the emitted sequence is a pure function of the total order over
/// keys and is independent of the input bucket-iteration order (§5.7 rule 5).
pub fn inner_equi_join(
    left: &[Option<Vec<JoinKey>>],
    right: &[Option<Vec<JoinKey>>],
) -> Vec<JoinMatch> {
    // Bucket the right side by key. IndexMap keeps insertion order for a
    // deterministic *probe traversal*, but the emitted result is sorted below,
    // so bucket order never leaks into the output.
    let mut buckets: IndexMap<Vec<JoinKey>, Vec<usize>> = IndexMap::new();
    for (j, rk) in right.iter().enumerate() {
        if let Some(k) = rk {
            buckets.entry(k.clone()).or_default().push(j);
        }
        // A null/missing right key is unmatchable: contributes no bucket entry.
    }

    let mut matches: Vec<JoinMatch> = Vec::new();
    for (i, lk) in left.iter().enumerate() {
        let Some(k) = lk else {
            // A null/missing left key is unmatchable: joins to nothing (0̄).
            continue;
        };
        if let Some(js) = buckets.get(k) {
            for &j in js {
                matches.push(JoinMatch {
                    key: k.clone(),
                    left: i,
                    right: j,
                });
            }
        }
    }

    // §5.7 rule 5: emit SORTED by canonical key (never bucket / first-seen
    // order). `(left, right)` breaks ties between the m·n tuples of one key so
    // the full sequence is deterministic for a fixed input labeling.
    matches.sort_by(|a, b| {
        a.key
            .cmp(&b.key)
            .then(a.left.cmp(&b.left))
            .then(a.right.cmp(&b.right))
    });
    matches
}

/// Group-by reduction under a semiring ⊕ (§5.3 / §5.7 rule 5): bucket rows by
/// their key, then **emit sorted by the canonical key**, reducing each bucket's
/// values with `reduce` in canonical (stable) input order. This is the
/// group-by-aggregate join (`group_by_sum` and its semiring generalizations) —
/// the value-equality counterpart of [`inner_equi_join`] for the case where the
/// matched rows are immediately folded.
///
/// Because every registry ⊕ is associative + commutative, permuting the input
/// rows cannot change any bucket's reduced value; reducing sequentially in the
/// (stable) input order additionally pins the *order of summation*, so swapping
/// to a float ⊕ introduces no last-ULP drift (§5.7 rule 5).
pub fn group_by_reduce(
    rows: &[(Vec<JoinKey>, f64)],
    reduce: ReduceKind,
) -> Vec<(Vec<JoinKey>, f64)> {
    let mut buckets: IndexMap<Vec<JoinKey>, Vec<f64>> = IndexMap::new();
    for (k, v) in rows {
        buckets.entry(k.clone()).or_default().push(*v);
    }

    // Emit sorted by canonical key, not by bucket insertion order.
    let mut keys: Vec<Vec<JoinKey>> = buckets.keys().cloned().collect();
    keys.sort();

    keys.into_iter()
        .map(|k| {
            let mut acc = reduce.identity();
            for &v in &buckets[&k] {
                acc = reduce.combine(acc, v);
            }
            (k, acc)
        })
        .collect()
}

/// Canonical byte serialization of a reduced relation: compact JSON
/// `[[k…,v],…]` — no spaces, UTF-8 (no `\uXXXX` escaping), each member tuple's
/// key components followed by its reduced value. This is the same canonical-JSON
/// discipline the round-trip idempotence contract relies on, and is what
/// "byte-identical serialized index set" means in the determinism harness
/// (`tests/conformance/determinism/`). An integral value serializes as an
/// integer (`5`, not `5.0`; `-0.0`→`0`) so the form matches integer-semiring
/// goldens exactly.
pub fn canonical_serialize_kv(rows: &[(Vec<JoinKey>, f64)]) -> String {
    let arr: Vec<Value> = rows
        .iter()
        .map(|(key, val)| {
            let mut comps: Vec<Value> = key.iter().map(JoinKey::to_json).collect();
            comps.push(num_to_json(*val));
            Value::Array(comps)
        })
        .collect();
    // serde_json's compact formatter emits no spaces and raw UTF-8 (it escapes
    // only control chars / `"` / `\`), matching the harness's
    // json.dumps(separators=(",",":"), ensure_ascii=False).
    serde_json::to_string(&Value::Array(arr)).unwrap_or_default()
}

/// Render a reduced value as the canonical JSON number: an exact integer when
/// the value is integral and i64-representable (normalizing `-0.0`→`0`),
/// otherwise the float. Keeps integer-semiring outputs free of a spurious `.0`.
fn num_to_json(v: f64) -> Value {
    if v.is_finite() && v.fract() == 0.0 && (i64::MIN as f64..=i64::MAX as f64).contains(&v) {
        Value::from(v as i64)
    } else {
        Value::from(v)
    }
}

/// Resolve / validate every `join.on` clause in `model` (RFC §5.3), in place.
/// Call once on an owned model **after** [`crate::aggregate::resolve_aggregate_ranges`]
/// (so all ranges are concrete intervals) and before shape inference.
///
/// For the **degenerate positional case** — every join key column is a declared
/// loop index of its aggregate node — the join is a structural no-op: the dense
/// einsum already combines those factors positionally, so the compiled artifact
/// and every emitted value are byte-identical to the no-join form. A join key
/// column that is *not* a declared loop index would need the runtime
/// value-equality engine over data-derived factor columns, which the dense Rust
/// evaluator does not yet drive (M3); it is rejected with a clear error rather
/// than silently mis-combined — mirroring the ragged/derived range rejection in
/// [`crate::aggregate`].
pub fn resolve_aggregate_joins(model: &mut Model) -> Result<(), CompileError> {
    for eq in &model.equations {
        validate_expr_joins(&eq.lhs)?;
        validate_expr_joins(&eq.rhs)?;
    }
    if let Some(init_eqs) = &model.initialization_equations {
        for eq in init_eqs {
            validate_expr_joins(&eq.lhs)?;
            validate_expr_joins(&eq.rhs)?;
        }
    }
    for var in model.variables.values() {
        if let Some(expr) = &var.expression {
            validate_expr_joins(expr)?;
        }
    }
    Ok(())
}

/// Recursively validate `join` clauses on a node and all its children.
fn validate_expr_joins(expr: &Expr) -> Result<(), CompileError> {
    let Expr::Operator(node) = expr else {
        return Ok(());
    };

    if let Some(joins) = &node.join {
        validate_node_joins(node, joins)?;
    }

    for a in &node.args {
        validate_expr_joins(a)?;
    }
    if let Some(b) = &node.expr {
        validate_expr_joins(b)?;
    }
    if let Some(f) = &node.filter {
        validate_expr_joins(f)?;
    }
    if let Some(l) = &node.lower {
        validate_expr_joins(l)?;
    }
    if let Some(u) = &node.upper {
        validate_expr_joins(u)?;
    }
    if let Some(vals) = &node.values {
        for v in vals {
            validate_expr_joins(v)?;
        }
    }
    if let Some(axes) = &node.axes {
        for v in axes.values() {
            validate_expr_joins(v)?;
        }
    }
    Ok(())
}

/// Validate one aggregate node's join clauses against its declared loop indices.
fn validate_node_joins(
    node: &ExpressionNode,
    joins: &[crate::types::JoinClause],
) -> Result<(), CompileError> {
    if !is_aggregate_op(&node.op) {
        return Err(CompileError::InterpreterBuildError {
            details: format!(
                "`join` is only valid on an aggregate/arrayop node, but appears on op '{}' \
                 (RFC semiring-faq-unified-ir §5.3)",
                node.op
            ),
        });
    }

    // The loop indices in scope: range keys (the iterated index symbols) plus
    // any output indices. A join key column naming one of these is positional.
    let mut declared: HashSet<&str> = HashSet::new();
    if let Some(ranges) = &node.ranges {
        for k in ranges.keys() {
            declared.insert(k.as_str());
        }
    }
    if let Some(out) = &node.output_idx {
        for k in out {
            declared.insert(k.as_str());
        }
    }

    for clause in joins {
        if clause.on.is_empty() {
            return Err(CompileError::InterpreterBuildError {
                details: "`join` clause has an empty `on` list; at least one [left, right] \
                          key-column pair is required (RFC semiring-faq-unified-ir §5.3)"
                    .to_string(),
            });
        }
        for pair in &clause.on {
            // The left key column drives matching. In the degenerate positional
            // case it is one of the node's loop indices, so the existing dense
            // gather already combines the factors positionally — no runtime
            // join. A non-loop-index column would need the data-derived
            // value-equality engine (M3).
            let left = pair[0].as_str();
            if !declared.contains(left) {
                return Err(CompileError::UnsupportedFeatureError {
                    feature: "value-equality join over data-derived columns".to_string(),
                    message: format!(
                        "join key column '{left}' is not a declared loop index of this \
                         aggregate ({declared:?}); a value-equality join over data-derived \
                         factor columns requires the per-key bucket/gather engine that the \
                         dense Rust evaluator does not yet drive (M2 supports the degenerate \
                         positional join — key columns that are loop indices; RFC \
                         semiring-faq-unified-ir §5.3)"
                    ),
                });
            }
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{ExpressionNode, JoinClause, RangeSpec};
    use std::collections::HashMap;

    // --- JoinKey total order (§5.5.1 rule 1) -------------------------------

    #[test]
    fn int_keys_order_by_value() {
        assert!(JoinKey::Int(2) < JoinKey::Int(10));
        assert!(JoinKey::Int(-1) < JoinKey::Int(0));
        let mut v = vec![JoinKey::Int(10), JoinKey::Int(2), JoinKey::Int(-5)];
        v.sort();
        assert_eq!(v, vec![JoinKey::Int(-5), JoinKey::Int(2), JoinKey::Int(10)]);
    }

    #[test]
    fn string_keys_order_by_code_point_not_locale() {
        // The §5.5.1 worked example: code-point order is 'B'<'Z'<'a'. A
        // case-insensitive locale would interleave 'a' among the capitals —
        // which is forbidden.
        let mut v = vec![
            JoinKey::Cat("a".into()),
            JoinKey::Cat("Z".into()),
            JoinKey::Cat("B".into()),
        ];
        v.sort();
        assert_eq!(
            v,
            vec![
                JoinKey::Cat("B".into()),
                JoinKey::Cat("Z".into()),
                JoinKey::Cat("a".into()),
            ]
        );
    }

    #[test]
    fn cross_type_order_is_total_int_before_cat() {
        assert!(JoinKey::Int(999) < JoinKey::Cat("".into()));
        // And tuples compare lexicographically (Vec<JoinKey>: Ord).
        let a = vec![JoinKey::Int(1), JoinKey::Cat("x".into())];
        let b = vec![JoinKey::Int(1), JoinKey::Cat("y".into())];
        assert!(a < b);
    }

    // --- Key-type discipline / rejection (§5.7 rule 1) ---------------------

    #[test]
    fn from_json_accepts_int_and_string() {
        assert_eq!(
            JoinKey::from_json(&Value::from(5)).unwrap(),
            JoinKey::Int(5)
        );
        assert_eq!(
            JoinKey::from_json(&Value::from("onroad")).unwrap(),
            JoinKey::Cat("onroad".into())
        );
    }

    #[test]
    fn from_json_rejects_float_keys() {
        // A fractional float and an integral-valued float token both reject —
        // a float repr is not a portable exact-equality key.
        assert_eq!(
            JoinKey::from_json(&serde_json::json!(1.5)),
            Err(KeyError::Float(1.5))
        );
        assert_eq!(
            JoinKey::from_json(&serde_json::json!(5.0)),
            Err(KeyError::Float(5.0))
        );
    }

    #[test]
    fn from_json_rejects_null_in_key() {
        // Emitting null INTO a key column is a build-time error (§5.3).
        assert_eq!(JoinKey::from_json(&Value::Null), Err(KeyError::Null));
    }

    #[test]
    fn from_json_bool_is_categorical_int() {
        assert_eq!(
            JoinKey::from_json(&Value::from(true)).unwrap(),
            JoinKey::Int(1)
        );
        assert_eq!(
            JoinKey::from_json(&Value::from(false)).unwrap(),
            JoinKey::Int(0)
        );
    }

    // --- Inner equi-join: cardinality, sorting, null-handling (§5.3) -------

    fn k(i: i64) -> Option<Vec<JoinKey>> {
        Some(vec![JoinKey::Int(i)])
    }

    #[test]
    fn many_to_many_cardinality_is_m_times_n() {
        // Key 7 appears twice on the left, three times on the right ⇒ 6 tuples.
        // Key 9 appears once each ⇒ 1. Key 3 (left only) and 4 (right only) ⇒ 0.
        let left = vec![k(7), k(3), k(7), k(9)];
        let right = vec![k(9), k(7), k(7), k(4), k(7)];
        let matches = inner_equi_join(&left, &right);
        let n7 = matches
            .iter()
            .filter(|m| m.key == vec![JoinKey::Int(7)])
            .count();
        let n9 = matches
            .iter()
            .filter(|m| m.key == vec![JoinKey::Int(9)])
            .count();
        assert_eq!(n7, 6, "m·n = 2·3");
        assert_eq!(n9, 1, "1·1");
        assert_eq!(
            matches.len(),
            7,
            "no spurious matches for left-only/right-only keys"
        );
    }

    #[test]
    fn join_emits_sorted_by_canonical_key() {
        let left = vec![k(30), k(10), k(20)];
        let right = vec![k(20), k(10), k(30)];
        let matches = inner_equi_join(&left, &right);
        let keys: Vec<&Vec<JoinKey>> = matches.iter().map(|m| &m.key).collect();
        let mut sorted = keys.clone();
        sorted.sort();
        assert_eq!(
            keys, sorted,
            "output must be sorted by canonical key, not input order"
        );
    }

    #[test]
    fn null_key_rows_are_unmatchable() {
        // A null key on either side contributes nothing (joins to 0̄, §5.3).
        let left = vec![k(1), None, k(2)];
        let right = vec![None, k(1), k(2), None];
        let matches = inner_equi_join(&left, &right);
        assert_eq!(matches.len(), 2);
        assert!(
            matches
                .iter()
                .all(|m| m.key == vec![JoinKey::Int(1)] || m.key == vec![JoinKey::Int(2)])
        );
    }

    #[test]
    fn join_is_independent_of_input_permutation_in_key_multiset() {
        // The emitted (sorted) key sequence — with multiplicity — is invariant
        // under permuting either relation (adversarial order-independence).
        let canon_keys = |l: &[Option<Vec<JoinKey>>], r: &[Option<Vec<JoinKey>>]| {
            inner_equi_join(l, r)
                .into_iter()
                .map(|m| m.key)
                .collect::<Vec<_>>()
        };
        let l1 = vec![k(7), k(7), k(9)];
        let r1 = vec![k(7), k(9), k(7)];
        let l2 = vec![k(9), k(7), k(7)]; // permuted
        let r2 = vec![k(7), k(7), k(9)]; // permuted
        assert_eq!(canon_keys(&l1, &r1), canon_keys(&l2, &r2));
    }

    // --- Group-by determinism golden (CONFORMANCE_SPEC §5.5 / manifest) ----

    fn gb_rows() -> Vec<(Vec<JoinKey>, f64)> {
        // The manifest `group_by_sum` canonical input rows.
        vec![
            (vec![JoinKey::Cat("B".into())], 2.0),
            (vec![JoinKey::Cat("a".into())], 5.0),
            (vec![JoinKey::Cat("B".into())], 3.0),
            (vec![JoinKey::Cat("Z".into())], 1.0),
            (vec![JoinKey::Cat("a".into())], 4.0),
        ]
    }

    #[test]
    fn group_by_sum_matches_manifest_golden_byte_for_byte() {
        let out = group_by_reduce(&gb_rows(), ReduceKind::Sum);
        // Sorted by code-point key: B(5), Z(1), a(9).
        assert_eq!(
            out,
            vec![
                (vec![JoinKey::Cat("B".into())], 5.0),
                (vec![JoinKey::Cat("Z".into())], 1.0),
                (vec![JoinKey::Cat("a".into())], 9.0),
            ]
        );
        // Byte-identical to tests/conformance/determinism/manifest.json
        // fixture `group_by_sum`.expected.serialized.
        assert_eq!(canonical_serialize_kv(&out), r#"[["B",5],["Z",1],["a",9]]"#);
    }

    #[test]
    fn group_by_sum_is_permutation_invariant() {
        // The manifest `permuted_rows` adversarial variant collapses to golden.
        let permuted = vec![
            (vec![JoinKey::Cat("a".into())], 4.0),
            (vec![JoinKey::Cat("Z".into())], 1.0),
            (vec![JoinKey::Cat("B".into())], 2.0),
            (vec![JoinKey::Cat("a".into())], 5.0),
            (vec![JoinKey::Cat("B".into())], 3.0),
        ];
        assert_eq!(
            canonical_serialize_kv(&group_by_reduce(&permuted, ReduceKind::Sum)),
            canonical_serialize_kv(&group_by_reduce(&gb_rows(), ReduceKind::Sum)),
        );
    }

    #[test]
    fn group_by_respects_semiring_oplus() {
        // Under min_sum's ⊕ = min, bucket B reduces to min(2,3)=2; a to min(5,4)=4.
        let out = group_by_reduce(&gb_rows(), ReduceKind::Min);
        assert_eq!(
            out,
            vec![
                (vec![JoinKey::Cat("B".into())], 2.0),
                (vec![JoinKey::Cat("Z".into())], 1.0),
                (vec![JoinKey::Cat("a".into())], 4.0),
            ]
        );
    }

    #[test]
    fn integral_values_serialize_without_trailing_point() {
        let rows = vec![(vec![JoinKey::Int(3)], -0.0), (vec![JoinKey::Int(4)], 2.0)];
        // -0.0 normalizes to 0; 2.0 → 2.
        assert_eq!(canonical_serialize_kv(&rows), r#"[[3,0],[4,2]]"#);
    }

    // --- Build-time resolution pass ----------------------------------------
    //
    // These exercise the per-node validator directly (the public
    // `resolve_aggregate_joins(model)` walk is covered end-to-end by the
    // join_filter.esm integration test, against a real parsed model).

    fn agg_with_join(joins: Vec<JoinClause>, ranges: Vec<&str>) -> Expr {
        let mut range_map = HashMap::new();
        for r in ranges {
            range_map.insert(r.to_string(), RangeSpec::Interval([1, 2]));
        }
        Expr::Operator(ExpressionNode {
            op: "aggregate".into(),
            ranges: Some(range_map),
            output_idx: Some(vec![]),
            join: Some(joins),
            expr: Some(Box::new(Expr::Variable("x".into()))),
            args: vec![Expr::Variable("x".into())],
            ..Default::default()
        })
    }

    #[test]
    fn accepts_degenerate_positional_join() {
        // join key columns src/fuel ARE declared loop indices ⇒ positional no-op.
        let join = vec![JoinClause {
            on: vec![
                ["src".into(), "sourceType".into()],
                ["fuel".into(), "fuelType".into()],
            ],
        }];
        let expr = agg_with_join(join, vec!["src", "fuel"]);
        assert!(validate_expr_joins(&expr).is_ok());
    }

    #[test]
    fn rejects_non_positional_join_as_unsupported() {
        // Left key column 'srcCol' is NOT a loop index ⇒ needs the data-derived
        // engine (M3) ⇒ clear UnsupportedFeatureError.
        let join = vec![JoinClause {
            on: vec![["srcCol".into(), "sourceType".into()]],
        }];
        let expr = agg_with_join(join, vec!["src", "fuel"]);
        let err = validate_expr_joins(&expr).unwrap_err();
        match err {
            CompileError::UnsupportedFeatureError { feature, message } => {
                assert!(feature.contains("value-equality join"));
                assert!(message.contains("srcCol"));
            }
            other => panic!("expected UnsupportedFeatureError, got {other:?}"),
        }
    }

    #[test]
    fn rejects_empty_on_list() {
        let join = vec![JoinClause { on: vec![] }];
        let expr = agg_with_join(join, vec!["src"]);
        assert!(validate_expr_joins(&expr).is_err());
    }

    #[test]
    fn rejects_join_on_non_aggregate_op() {
        // A `join` smuggled onto a non-aggregate op is a build error.
        let bogus = Expr::Operator(ExpressionNode {
            op: "+".into(),
            join: Some(vec![JoinClause {
                on: vec![["a".into(), "b".into()]],
            }]),
            args: vec![Expr::Variable("x".into())],
            ..Default::default()
        });
        assert!(validate_expr_joins(&bogus).is_err());
    }

    #[test]
    fn noop_when_no_join_present() {
        // An aggregate node with no join clause validates trivially, and the
        // walk recurses into nested children without spurious errors.
        let agg = Expr::Operator(ExpressionNode {
            op: "aggregate".into(),
            ranges: Some(HashMap::from([(
                "i".to_string(),
                RangeSpec::Interval([1, 3]),
            )])),
            output_idx: Some(vec![]),
            expr: Some(Box::new(Expr::Variable("x".into()))),
            args: vec![Expr::Variable("x".into())],
            ..Default::default()
        });
        assert!(validate_expr_joins(&agg).is_ok());
    }
}
