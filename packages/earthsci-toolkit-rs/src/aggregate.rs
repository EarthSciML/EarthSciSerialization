//! Semiring registry and index-set range resolution for `aggregate` /
//! `arrayop` nodes — the M1 core of RFC `semiring-faq-unified-ir`.
//!
//! This module is the strict-superset refactor of the existing reducer:
//!
//! - **§5.1 Semiring.** [`Semiring`] is the closed, exhaustive registry of the
//!   five named `(⊕, ⊗)` pairs with their **normative** identities `(0̄, 1̄)`.
//!   The `reduce` field names ⊕ only; ⊗ and both identities come from the
//!   registry table here, never from the file. [`effective_reduce_kind`] is the
//!   single entry point the evaluator uses to pick the ⊕ reducer for a node:
//!   the semiring wins when present, otherwise the legacy `reduce` string
//!   drives it exactly as before (the strict-superset promise).
//! - **§5.2 Index sets.** [`resolve_aggregate_ranges`] rewrites every
//!   `{ "from": <name> }` range reference into a concrete `[lo, hi]` interval
//!   against the model `index_sets` registry, **erroring on an undeclared
//!   name** (no implicit interval inference). `interval` and `categorical`
//!   sets resolve to dense static bounds; `ragged`/`derived` sets (which need
//!   per-parent dynamic bounds + gather) are not yet implemented in the Rust
//!   evaluator and produce a clear error.
//! - **§5.6 Op tag.** [`is_aggregate_op`] accepts the canonical `"aggregate"`
//!   tag and the deprecated `"arrayop"` alias identically.

use std::collections::HashMap;

use crate::simulate::CompileError;
use crate::types::{Expr, IndexSet, Model, RangeSpec};

/// The ⊕/⊗ operators the evaluator can fold with, each carrying its normative
/// identity (RFC §5.1). A single enum serves both the aggregation side (⊕) and
/// the product side (⊗) so the empty-reduction identity 0̄ and empty-product
/// identity 1̄ are pinned from one place.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ReduceKind {
    Sum,
    Product,
    Max,
    Min,
    Or,
    And,
}

impl ReduceKind {
    /// The identity element — the value an empty fold returns. As a ⊕ this is
    /// 0̄ (empty reduction); as a ⊗ this is 1̄ (empty product).
    pub fn identity(self) -> f64 {
        match self {
            ReduceKind::Sum => 0.0,
            ReduceKind::Product => 1.0,
            ReduceKind::Max => f64::NEG_INFINITY,
            ReduceKind::Min => f64::INFINITY,
            ReduceKind::Or => 0.0,  // false
            ReduceKind::And => 1.0, // true
        }
    }

    /// Fold one term into the accumulator. The Boolean ops treat any non-zero
    /// value as true and return a crisp `0.0`/`1.0`.
    pub fn combine(self, acc: f64, term: f64) -> f64 {
        match self {
            ReduceKind::Sum => acc + term,
            ReduceKind::Product => acc * term,
            ReduceKind::Max => f64::max(acc, term),
            ReduceKind::Min => f64::min(acc, term),
            ReduceKind::Or => {
                if acc != 0.0 || term != 0.0 {
                    1.0
                } else {
                    0.0
                }
            }
            ReduceKind::And => {
                if acc != 0.0 && term != 0.0 {
                    1.0
                } else {
                    0.0
                }
            }
        }
    }
}

/// The closed, exhaustive semiring registry (RFC §5.1). A semiring is fully
/// specified by its two operators **and** their identities; adding one is a
/// spec change, not a per-file extension.
///
/// | `semiring` | ⊕ (`reduce`) | 0̄ | ⊗ | 1̄ |
/// |---|---|---|---|---|
/// | `sum_product` *(default)* | `+` | `0` | `×` | `1` |
/// | `max_product` | `max` | `-∞` | `×` | `1` |
/// | `min_sum` | `min` | `+∞` | `+` | `0` |
/// | `max_sum` | `max` | `-∞` | `+` | `0` |
/// | `bool_and_or` | `∨` | `false` | `∧` | `true` |
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Semiring {
    SumProduct,
    MaxProduct,
    MinSum,
    MaxSum,
    BoolAndOr,
}

impl Semiring {
    /// Parse a registry name; `None` for an unregistered name (the schema's
    /// closed enum normally rejects these before the evaluator is reached).
    pub fn from_name(name: &str) -> Option<Self> {
        Some(match name {
            "sum_product" => Semiring::SumProduct,
            "max_product" => Semiring::MaxProduct,
            "min_sum" => Semiring::MinSum,
            "max_sum" => Semiring::MaxSum,
            "bool_and_or" => Semiring::BoolAndOr,
            _ => return None,
        })
    }

    /// ⊕ — the aggregation operator named by `reduce`.
    pub fn oplus(self) -> ReduceKind {
        match self {
            Semiring::SumProduct => ReduceKind::Sum,
            Semiring::MaxProduct => ReduceKind::Max,
            Semiring::MinSum => ReduceKind::Min,
            Semiring::MaxSum => ReduceKind::Max,
            Semiring::BoolAndOr => ReduceKind::Or,
        }
    }

    /// ⊗ — the product operator. Applied in the node body for M1; defined here
    /// so the normative empty-product identity 1̄ (`otimes().identity()`) is
    /// pinned per §5.1 and asserted by conformance.
    pub fn otimes(self) -> ReduceKind {
        match self {
            Semiring::SumProduct => ReduceKind::Product,
            Semiring::MaxProduct => ReduceKind::Product,
            Semiring::MinSum => ReduceKind::Sum,
            Semiring::MaxSum => ReduceKind::Sum,
            Semiring::BoolAndOr => ReduceKind::And,
        }
    }
}

/// Resolve the effective ⊕ reducer for an `aggregate`/`arrayop` node.
///
/// Per RFC §5.1, when `semiring` is present it is authoritative: ⊕ and its
/// identity come from the registry, never the file. When absent, the legacy
/// `reduce` string names ⊕ directly (today's behavior — the strict-superset
/// promise). Total and infallible: an absent/unrecognized `reduce` falls back
/// to `Sum`, exactly matching the evaluator's pre-existing default.
pub fn effective_reduce_kind(semiring: Option<&str>, reduce: Option<&str>) -> ReduceKind {
    // A recognized semiring is authoritative for ⊕. An unrecognized name (the
    // schema's closed enum should have rejected it) falls through to the legacy
    // `reduce` string rather than mis-aggregating.
    if let Some(sr) = semiring.and_then(Semiring::from_name) {
        return sr.oplus();
    }
    match reduce {
        Some("*") => ReduceKind::Product,
        Some("max") => ReduceKind::Max,
        Some("min") => ReduceKind::Min,
        // "+", None, or anything else → today's default reducer.
        _ => ReduceKind::Sum,
    }
}

/// Whether `op` is the aggregate/arrayop node tag. `"aggregate"` is the
/// canonical tag (RFC §5.6); `"arrayop"` is retained as a deprecated alias so
/// existing files keep evaluating unchanged.
pub fn is_aggregate_op(op: &str) -> bool {
    op == "arrayop" || op == "aggregate"
}

/// Rewrite every `{ "from": <name> }` range reference in `model` into a
/// concrete `[lo, hi]` interval, resolved against the model `index_sets`
/// registry (RFC §5.2). Operates in place; call once on an owned model before
/// shape inference and rule building so every downstream consumer sees only
/// [`RangeSpec::Interval`].
///
/// Errors on an undeclared `from` name (no implicit interval inference) and on
/// `ragged`/`derived` sets, which require machinery not yet present in the Rust
/// evaluator.
pub fn resolve_aggregate_ranges(model: &mut Model) -> Result<(), CompileError> {
    // Clone the registry so the equations can be mutated without aliasing
    // `model`. An absent registry is fine: any `{from}` reference then errors
    // as undeclared (correct), and pure-interval files resolve as no-ops.
    let index_sets = model.index_sets.clone().unwrap_or_default();

    for eq in &mut model.equations {
        resolve_expr_ranges(&mut eq.lhs, &index_sets)?;
        resolve_expr_ranges(&mut eq.rhs, &index_sets)?;
    }
    if let Some(init_eqs) = &mut model.initialization_equations {
        for eq in init_eqs {
            resolve_expr_ranges(&mut eq.lhs, &index_sets)?;
            resolve_expr_ranges(&mut eq.rhs, &index_sets)?;
        }
    }
    for var in model.variables.values_mut() {
        if let Some(expr) = &mut var.expression {
            resolve_expr_ranges(expr, &index_sets)?;
        }
    }
    Ok(())
}

/// Recursively resolve `{from}` range references on a node and all its children.
fn resolve_expr_ranges(
    expr: &mut Expr,
    index_sets: &HashMap<String, IndexSet>,
) -> Result<(), CompileError> {
    let Expr::Operator(node) = expr else {
        return Ok(());
    };

    // Resolve this node's own ranges in place.
    if let Some(ranges) = &mut node.ranges {
        for (idx_name, spec) in ranges.iter_mut() {
            let resolved = match spec {
                RangeSpec::Interval(_) => continue,
                RangeSpec::IndexSetRef { from, of } => {
                    resolve_index_set_ref(from, of.as_deref(), idx_name, index_sets)?
                }
            };
            *spec = RangeSpec::Interval(resolved);
        }
    }

    // Recurse into every expression-bearing child.
    for a in &mut node.args {
        resolve_expr_ranges(a, index_sets)?;
    }
    if let Some(b) = &mut node.expr {
        resolve_expr_ranges(b, index_sets)?;
    }
    if let Some(l) = &mut node.lower {
        resolve_expr_ranges(l, index_sets)?;
    }
    if let Some(u) = &mut node.upper {
        resolve_expr_ranges(u, index_sets)?;
    }
    if let Some(vals) = &mut node.values {
        for v in vals.iter_mut() {
            resolve_expr_ranges(v, index_sets)?;
        }
    }
    if let Some(axes) = &mut node.axes {
        for v in axes.values_mut() {
            resolve_expr_ranges(v, index_sets)?;
        }
    }
    Ok(())
}

/// Resolve one `{ from, of }` reference to concrete `[lo, hi]` bounds.
///
/// Interval and categorical sets resolve to a 1-based dense interval
/// (`[1, size]` / `[1, |members|]`), matching the existing file-level range
/// convention. A dependent (`of`) reference, or a `ragged`/`derived` set, needs
/// per-parent dynamic bounds + gather that the Rust evaluator does not yet
/// implement (M1) and is rejected with a clear error.
fn resolve_index_set_ref(
    from: &str,
    of: Option<&[String]>,
    idx_name: &str,
    index_sets: &HashMap<String, IndexSet>,
) -> Result<[i64; 2], CompileError> {
    if of.is_some_and(|parents| !parents.is_empty()) {
        return Err(CompileError::UnsupportedFeatureError {
            feature: "ragged index-set range".to_string(),
            message: format!(
                "aggregate range '{idx_name}' references index set '{from}' with a dependent `of` \
                 (ragged) binding; per-parent dynamic bounds + gather are not yet implemented in \
                 the Rust evaluator (M1 supports interval/categorical; RFC \
                 semiring-faq-unified-ir §5.2)"
            ),
        });
    }

    let set = index_sets
        .get(from)
        .ok_or_else(|| CompileError::InterpreterBuildError {
            details: format!(
                "aggregate range '{idx_name}' references index set '{from}', which is not declared \
                 in the model `index_sets` registry (no implicit interval inference; RFC \
                 semiring-faq-unified-ir §5.2)"
            ),
        })?;

    match set.kind.as_str() {
        "interval" => {
            let size = set
                .size
                .ok_or_else(|| CompileError::InterpreterBuildError {
                    details: format!("index set '{from}' has kind \"interval\" but no `size`"),
                })?;
            Ok([1, size])
        }
        "categorical" => {
            let n = set
                .members
                .as_ref()
                .map(|m| m.len() as i64)
                .ok_or_else(|| CompileError::InterpreterBuildError {
                    details: format!(
                        "index set '{from}' has kind \"categorical\" but no `members`"
                    ),
                })?;
            Ok([1, n])
        }
        "ragged" => Err(CompileError::UnsupportedFeatureError {
            feature: "ragged index set".to_string(),
            message: format!(
                "index set '{from}' (aggregate range '{idx_name}') has kind \"ragged\"; per-parent \
                 dynamic bounds + gather are not yet implemented in the Rust evaluator (M1 supports \
                 interval/categorical; RFC semiring-faq-unified-ir §5.2)"
            ),
        }),
        "derived" => Err(CompileError::UnsupportedFeatureError {
            feature: "derived index set".to_string(),
            message: format!(
                "index set '{from}' (aggregate range '{idx_name}') has kind \"derived\"; \
                 FAQ-materialized index sets are not yet implemented in the Rust evaluator (M2+; \
                 RFC semiring-faq-unified-ir §5.5)"
            ),
        }),
        other => Err(CompileError::InterpreterBuildError {
            details: format!("index set '{from}' has unknown kind '{other}'"),
        }),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn interval(size: i64) -> IndexSet {
        IndexSet {
            kind: "interval".into(),
            size: Some(size),
            members: None,
            from_faq: None,
            of: None,
            offsets: None,
            values: None,
        }
    }

    #[test]
    fn semiring_identities_match_rfc_table() {
        // (semiring, 0̄ = ⊕ identity, 1̄ = ⊗ identity) per RFC §5.1.
        let cases = [
            (Semiring::SumProduct, 0.0, 1.0),
            (Semiring::MaxProduct, f64::NEG_INFINITY, 1.0),
            (Semiring::MinSum, f64::INFINITY, 0.0),
            (Semiring::MaxSum, f64::NEG_INFINITY, 0.0),
            (Semiring::BoolAndOr, 0.0, 1.0), // false, true
        ];
        for (sr, zero_bar, one_bar) in cases {
            assert_eq!(sr.oplus().identity(), zero_bar, "{sr:?} 0̄");
            assert_eq!(sr.otimes().identity(), one_bar, "{sr:?} 1̄");
        }
    }

    #[test]
    fn semiring_is_authoritative_over_reduce() {
        // Semiring present → its ⊕ wins regardless of (or absent) `reduce`.
        assert_eq!(
            effective_reduce_kind(Some("min_sum"), None),
            ReduceKind::Min
        );
        assert_eq!(
            effective_reduce_kind(Some("max_sum"), Some("+")),
            ReduceKind::Max
        );
        assert_eq!(
            effective_reduce_kind(Some("max_product"), None),
            ReduceKind::Max
        );
        assert_eq!(
            effective_reduce_kind(Some("bool_and_or"), None),
            ReduceKind::Or
        );
        // No semiring → legacy reduce string, default "+".
        assert_eq!(effective_reduce_kind(None, None), ReduceKind::Sum);
        assert_eq!(effective_reduce_kind(None, Some("+")), ReduceKind::Sum);
        assert_eq!(effective_reduce_kind(None, Some("*")), ReduceKind::Product);
        assert_eq!(effective_reduce_kind(None, Some("max")), ReduceKind::Max);
        assert_eq!(effective_reduce_kind(None, Some("min")), ReduceKind::Min);
        // Unknown semiring falls back to the legacy reduce rather than panicking.
        assert_eq!(
            effective_reduce_kind(Some("bogus"), Some("min")),
            ReduceKind::Min
        );
    }

    #[test]
    fn or_and_reductions_are_crisp_boolean() {
        assert_eq!(ReduceKind::Or.combine(0.0, 0.0), 0.0);
        assert_eq!(ReduceKind::Or.combine(0.0, 3.0), 1.0);
        assert_eq!(ReduceKind::Or.combine(2.0, 0.0), 1.0);
        assert_eq!(ReduceKind::And.combine(1.0, 1.0), 1.0);
        assert_eq!(ReduceKind::And.combine(1.0, 0.0), 0.0);
        assert_eq!(ReduceKind::And.combine(0.0, 0.0), 0.0);
    }

    #[test]
    fn aggregate_op_alias() {
        assert!(is_aggregate_op("aggregate"));
        assert!(is_aggregate_op("arrayop"));
        assert!(!is_aggregate_op("makearray"));
        assert!(!is_aggregate_op("+"));
    }

    #[test]
    fn resolve_interval_and_categorical_from() {
        let mut index_sets = HashMap::new();
        index_sets.insert("cells".to_string(), interval(5));
        index_sets.insert(
            "county".to_string(),
            IndexSet {
                kind: "categorical".into(),
                size: None,
                members: Some(vec![
                    serde_json::json!("Champaign"),
                    serde_json::json!("Cook"),
                    serde_json::json!("Sangamon"),
                ]),
                from_faq: None,
                of: None,
                offsets: None,
                values: None,
            },
        );
        assert_eq!(
            resolve_index_set_ref("cells", None, "i", &index_sets).unwrap(),
            [1, 5]
        );
        assert_eq!(
            resolve_index_set_ref("county", None, "c", &index_sets).unwrap(),
            [1, 3]
        );
    }

    #[test]
    fn undeclared_from_errors_naming_the_set() {
        let index_sets: HashMap<String, IndexSet> = HashMap::new();
        let err = resolve_index_set_ref("nonesuch", None, "i", &index_sets).unwrap_err();
        let msg = format!("{err:?}");
        assert!(msg.contains("nonesuch"), "error should name the set: {msg}");
    }

    #[test]
    fn ragged_and_derived_and_dependent_of_are_unsupported() {
        let mut index_sets = HashMap::new();
        index_sets.insert(
            "edges".to_string(),
            IndexSet {
                kind: "ragged".into(),
                size: None,
                members: None,
                from_faq: None,
                of: Some(vec!["cells".into()]),
                offsets: Some("nEdgesOnCell".into()),
                values: Some("edgesOnCell".into()),
            },
        );
        assert!(resolve_index_set_ref("edges", None, "k", &index_sets).is_err());

        // A dependent `of` on the *reference* is ragged even for a static set.
        let mut iv = HashMap::new();
        iv.insert("cells".to_string(), interval(3));
        assert!(resolve_index_set_ref("cells", Some(&["i".to_string()]), "k", &iv).is_err());
    }
}
