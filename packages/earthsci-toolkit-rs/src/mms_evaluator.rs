//! 1D stencil walker with ghost-cell synthesis (RFC §5.2.8 / §7).
//!
//! Mirrors the Julia reference implementation in
//! `packages/EarthSciSerialization.jl/src/mms_evaluator.jl`. Provides a
//! pure-data 1D Cartesian stencil applier that reads `ghost_width` and
//! `boundary_policy` off a rule and synthesises ghost cells before
//! evaluating the stencil. `panel_dispatch` is recognised but rejected
//! at evaluation time — cubed-sphere panel-boundary distance switching
//! lives in a future 2D adapter (esm-8fi follow-up).
//!
//! Stencils are passed in their JSON wire form: a list of entries each
//! carrying `selector.offset` (i64) and `coeff` (an AST node). Coefficients
//! are evaluated once per call against the supplied bindings table.

use crate::expression::evaluate;
use crate::rule_engine::{BoundaryPolicyKind, BoundaryPolicySpec, parse_expr};
use std::collections::HashMap;

/// Errors raised by the stencil walker.
///
/// `code()` returns one of the RFC stable error codes:
/// - `E_MMS_BAD_FIXTURE` (malformed inputs, missing prescribe callback,
///   unknown boundary_policy kind, etc.)
/// - `E_GHOST_WIDTH_TOO_SMALL` (rule's `ghost_width` < `max(|offset|)`)
/// - `E_GHOST_FILL_UNSUPPORTED` (`panel_dispatch` 1D evaluation)
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct MmsEvaluatorError {
    pub code: String,
    pub message: String,
}

impl MmsEvaluatorError {
    pub fn new(code: impl Into<String>, message: impl Into<String>) -> Self {
        Self {
            code: code.into(),
            message: message.into(),
        }
    }
    pub fn code(&self) -> &str {
        &self.code
    }
}

impl std::fmt::Display for MmsEvaluatorError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "MmsEvaluatorError({}): {}", self.code, self.message)
    }
}

impl std::error::Error for MmsEvaluatorError {}

/// Boundary side a prescribed-ghost callback is filling.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Side {
    Left,
    Right,
}

/// Resolve the v0.3.x backwards-compatible aliases to their canonical
/// kind. Mirrors the Julia `_canonical_boundary_kind` and the closed-set
/// alias table on the schema parser.
pub fn canonicalize_boundary_policy_kind(kind: BoundaryPolicyKind) -> BoundaryPolicyKind {
    match kind {
        BoundaryPolicyKind::Ghosted => BoundaryPolicyKind::Prescribed,
        BoundaryPolicyKind::NeumannZero => BoundaryPolicyKind::Reflecting,
        BoundaryPolicyKind::Extrapolate => BoundaryPolicyKind::OneSidedExtrapolation,
        k => k,
    }
}

/// Apply a 1D Cartesian stencil to the periodic sample vector `u`. Each
/// entry of `stencil_json` must carry `selector.offset` (i64) and `coeff`
/// (an AST node). The coefficient is evaluated once per call against
/// `bindings`. The result has the same length as `u`.
///
/// `stencil_json` may also be a JSON object mapping sub-stencil names to
/// entry lists — the PPM-style multi-output rule layout where one rule
/// emits several stencils. Pass `sub_stencil` to select one; an unspecified
/// or unknown name on a multi-stencil rule yields `E_MMS_BAD_FIXTURE`.
pub fn apply_stencil_periodic_1d(
    stencil_json: &serde_json::Value,
    u: &[f64],
    bindings: &HashMap<String, f64>,
    sub_stencil: Option<&str>,
) -> Result<Vec<f64>, MmsEvaluatorError> {
    let entries = resolve_substencil(stencil_json, sub_stencil)?;
    let n = u.len();
    let coeff_pairs = build_coeff_pairs(entries, bindings)?;
    let mut out = vec![0.0_f64; n];
    if n == 0 {
        return Ok(out);
    }
    let n_i = n as isize;
    for (i, slot) in out.iter_mut().enumerate() {
        let mut acc = 0.0_f64;
        for &(off, c) in &coeff_pairs {
            let mut j = (i as isize + off) % n_i;
            if j < 0 {
                j += n_i;
            }
            acc += c * u[j as usize];
        }
        *slot = acc;
    }
    Ok(out)
}

/// Apply a 1D Cartesian stencil after extending `u` on each side by
/// `ghost_width` cells using the rule's declared `boundary_policy` (RFC
/// §5.2.8). Returns the length-`u.len()` interior outputs, having sliced
/// ghosts back off.
///
/// Supported policy kinds (closed set per RFC §5.2.8):
///
/// - `Periodic` — wrap-around fill. Bit-equal to
///   [`apply_stencil_periodic_1d`] on identical inputs.
/// - `Reflecting` (alias `NeumannZero`) — mirror across the boundary
///   face: ghost cell `k` (1 = closest to the edge) gets `u[k-1]` on the
///   left and `u[n-k]` on the right.
/// - `OneSidedExtrapolation` (alias `Extrapolate`) — polynomial
///   extrapolation from the interior. `policy.degree` ∈ `0..=3`; default
///   `1` (linear). Degree 0 is constant; degree 2/3 fit a quadratic /
///   cubic to the first `degree + 1` interior cells and evaluate at the
///   ghost cell centers.
/// - `Prescribed` (alias `Ghosted`) — caller-supplied ghost values via
///   `prescribe`. The callable receives `(side, k)` with
///   `k ∈ 1..=ghost_width` (1 = closest to the boundary), returning the
///   ghost value.
///
/// `ghost_width` MUST be ≥ `max(|offset|)` across all stencil entries,
/// else `MmsEvaluatorError(E_GHOST_WIDTH_TOO_SMALL)` is returned naming
/// the offending offset.
///
/// `PanelDispatch` is recognised but not implemented — returns
/// `MmsEvaluatorError(E_GHOST_FILL_UNSUPPORTED)`.
pub fn apply_stencil_ghosted_1d(
    stencil_json: &serde_json::Value,
    u: &[f64],
    bindings: &HashMap<String, f64>,
    ghost_width: i64,
    policy: &BoundaryPolicySpec,
    prescribe: Option<&dyn Fn(Side, usize) -> f64>,
    sub_stencil: Option<&str>,
) -> Result<Vec<f64>, MmsEvaluatorError> {
    if ghost_width < 0 {
        return Err(MmsEvaluatorError::new(
            "E_MMS_BAD_FIXTURE",
            format!("ghost_width must be non-negative, got {ghost_width}"),
        ));
    }
    let entries = resolve_substencil(stencil_json, sub_stencil)?;
    let coeff_pairs = build_coeff_pairs(entries, bindings)?;
    let max_off = coeff_pairs
        .iter()
        .map(|(off, _)| off.unsigned_abs() as i64)
        .max()
        .unwrap_or(0);
    if ghost_width < max_off {
        return Err(MmsEvaluatorError::new(
            "E_GHOST_WIDTH_TOO_SMALL",
            format!(
                "stencil offset {max_off} exceeds ghost_width {ghost_width}; \
                 rule must declare `ghost_width` ≥ max(|offset|)"
            ),
        ));
    }

    let n = u.len();
    if n < 2 {
        return Err(MmsEvaluatorError::new(
            "E_MMS_BAD_FIXTURE",
            format!("ghosted stencil application requires at least 2 interior cells; got {n}"),
        ));
    }
    let ng = ghost_width as usize;
    let mut u_ext = vec![0.0_f64; n + 2 * ng];
    u_ext[ng..ng + n].copy_from_slice(u);

    let kind = canonicalize_boundary_policy_kind(policy.kind);
    let degree = policy.degree.unwrap_or(1);
    match kind {
        BoundaryPolicyKind::Periodic => fill_ghosts_periodic(&mut u_ext, u, ng),
        BoundaryPolicyKind::Reflecting => fill_ghosts_reflecting(&mut u_ext, u, ng),
        BoundaryPolicyKind::OneSidedExtrapolation => {
            fill_ghosts_one_sided(&mut u_ext, u, ng, degree)?
        }
        BoundaryPolicyKind::Prescribed => {
            let cb = prescribe.ok_or_else(|| {
                MmsEvaluatorError::new(
                    "E_MMS_BAD_FIXTURE",
                    "boundary_policy=`prescribed` requires a `prescribe` callback; \
                     it receives (side, k) with k ∈ 1..=ghost_width",
                )
            })?;
            fill_ghosts_prescribed(&mut u_ext, ng, cb);
        }
        BoundaryPolicyKind::PanelDispatch => {
            return Err(MmsEvaluatorError::new(
                "E_GHOST_FILL_UNSUPPORTED",
                "boundary_policy=`panel_dispatch` not implemented for the 1D walker \
                 (cubed-sphere only); see esm-8fi follow-up for the 2D adapter",
            ));
        }
        // The alias variants are resolved by canonicalize_boundary_policy_kind.
        BoundaryPolicyKind::Ghosted
        | BoundaryPolicyKind::NeumannZero
        | BoundaryPolicyKind::Extrapolate => {
            unreachable!("canonicalize_boundary_policy_kind resolves aliases")
        }
    }

    let mut out = vec![0.0_f64; n];
    for (i, slot) in out.iter_mut().enumerate() {
        let mut acc = 0.0_f64;
        for &(off, c) in &coeff_pairs {
            let idx = (ng as isize + i as isize + off) as usize;
            acc += c * u_ext[idx];
        }
        *slot = acc;
    }
    Ok(out)
}

fn resolve_substencil<'a>(
    stencil_json: &'a serde_json::Value,
    sub_stencil: Option<&str>,
) -> Result<&'a Vec<serde_json::Value>, MmsEvaluatorError> {
    if let Some(arr) = stencil_json.as_array() {
        if sub_stencil.is_some() {
            return Err(MmsEvaluatorError::new(
                "E_MMS_BAD_FIXTURE",
                format!(
                    "`sub_stencil={:?}` was requested but rule carries a single \
                     stencil list, not a multi-stencil mapping",
                    sub_stencil.unwrap()
                ),
            ));
        }
        return Ok(arr);
    }
    if let Some(obj) = stencil_json.as_object() {
        let name = sub_stencil.ok_or_else(|| {
            MmsEvaluatorError::new(
                "E_MMS_BAD_FIXTURE",
                format!(
                    "rule has multi-stencil mapping; caller must select one via \
                     `sub_stencil` (available: {})",
                    obj.keys().cloned().collect::<Vec<_>>().join(", ")
                ),
            )
        })?;
        let entry = obj.get(name).ok_or_else(|| {
            MmsEvaluatorError::new(
                "E_MMS_BAD_FIXTURE",
                format!(
                    "rule has no sub-stencil `{name}` (available: {})",
                    obj.keys().cloned().collect::<Vec<_>>().join(", ")
                ),
            )
        })?;
        return entry.as_array().ok_or_else(|| {
            MmsEvaluatorError::new(
                "E_MMS_BAD_FIXTURE",
                format!("sub-stencil `{name}` must be an array of stencil entries"),
            )
        });
    }
    Err(MmsEvaluatorError::new(
        "E_MMS_BAD_FIXTURE",
        "stencil_json must be an array of entries or a mapping of named sub-stencil arrays",
    ))
}

fn build_coeff_pairs(
    entries: &[serde_json::Value],
    bindings: &HashMap<String, f64>,
) -> Result<Vec<(isize, f64)>, MmsEvaluatorError> {
    let mut out = Vec::with_capacity(entries.len());
    for s in entries {
        let sel = s.get("selector").ok_or_else(|| {
            MmsEvaluatorError::new(
                "E_MMS_BAD_FIXTURE",
                "stencil entry missing `selector`",
            )
        })?;
        let off = sel.get("offset").and_then(|v| v.as_i64()).ok_or_else(|| {
            MmsEvaluatorError::new(
                "E_MMS_BAD_FIXTURE",
                "stencil entry `selector.offset` must be an integer",
            )
        })?;
        let coeff_raw = s.get("coeff").ok_or_else(|| {
            MmsEvaluatorError::new(
                "E_MMS_BAD_FIXTURE",
                "stencil entry missing `coeff`",
            )
        })?;
        let coeff = eval_coeff(coeff_raw, bindings)?;
        out.push((off as isize, coeff));
    }
    Ok(out)
}

fn eval_coeff(
    node: &serde_json::Value,
    bindings: &HashMap<String, f64>,
) -> Result<f64, MmsEvaluatorError> {
    let expr = parse_expr(node).map_err(|e| {
        MmsEvaluatorError::new(
            "E_MMS_BAD_FIXTURE",
            format!("could not parse stencil coefficient AST: {e}"),
        )
    })?;
    evaluate(&expr, bindings).map_err(|unbound| {
        MmsEvaluatorError::new(
            "E_MMS_BAD_FIXTURE",
            format!(
                "stencil coefficient references unbound symbols: {}",
                unbound.join(", ")
            ),
        )
    })
}

fn fill_ghosts_periodic(u_ext: &mut [f64], u: &[f64], ng: usize) {
    let n = u.len();
    for k in 1..=ng {
        // left ghost k mirrors interior cell n-k+1 across the period
        u_ext[ng - k] = u[n - k];
        // right ghost k mirrors interior cell k across the period
        u_ext[ng + n + k - 1] = u[k - 1];
    }
}

fn fill_ghosts_reflecting(u_ext: &mut [f64], u: &[f64], ng: usize) {
    let n = u.len();
    for k in 1..=ng {
        // Mirror across the boundary face: ghost cell k (1 = closest to
        // the boundary) reads interior cell k.
        u_ext[ng - k] = u[k - 1];
        u_ext[ng + n + k - 1] = u[n - k];
    }
}

fn fill_ghosts_one_sided(
    u_ext: &mut [f64],
    u: &[f64],
    ng: usize,
    degree: i64,
) -> Result<(), MmsEvaluatorError> {
    if !(0..=3).contains(&degree) {
        return Err(MmsEvaluatorError::new(
            "E_MMS_BAD_FIXTURE",
            format!("one_sided_extrapolation degree must be in 0..3, got {degree}"),
        ));
    }
    let n = u.len();
    let needed = (degree + 1) as usize;
    if n < needed {
        return Err(MmsEvaluatorError::new(
            "E_MMS_BAD_FIXTURE",
            format!(
                "one_sided_extrapolation degree {degree} requires at least {needed} \
                 interior cells; got {n}"
            ),
        ));
    }
    for k in 1..=ng {
        u_ext[ng - k] = extrapolate_left(u, degree, k);
        u_ext[ng + n + k - 1] = extrapolate_right(u, degree, k);
    }
    Ok(())
}

// Newton forward-difference extrapolation from the left interior cells
// (1..=degree+1 in 1-based indexing → 0..=degree here) to virtual cell
// index 1 - k. Closed forms match the standard polynomial extrapolation
// through `degree + 1` equally-spaced points, mirroring the Julia
// reference bit-for-bit.
fn extrapolate_left(u: &[f64], degree: i64, k: usize) -> f64 {
    let kk = k as f64;
    match degree {
        0 => u[0],
        1 => u[0] + kk * (u[0] - u[1]),
        2 => {
            (1.0 + 1.5 * kk + 0.5 * kk * kk) * u[0]
                + (-2.0 * kk - kk * kk) * u[1]
                + (0.5 * kk + 0.5 * kk * kk) * u[2]
        }
        3 => {
            (1.0 + (11.0 / 6.0) * kk + kk * kk + (1.0 / 6.0) * kk * kk * kk) * u[0]
                + (-3.0 * kk - 2.5 * kk * kk - 0.5 * kk * kk * kk) * u[1]
                + (1.5 * kk + 2.0 * kk * kk + 0.5 * kk * kk * kk) * u[2]
                + ((-1.0 / 3.0) * kk - 0.5 * kk * kk - (1.0 / 6.0) * kk * kk * kk) * u[3]
        }
        _ => unreachable!("guarded by 0..=3 check above"),
    }
}

fn extrapolate_right(u: &[f64], degree: i64, k: usize) -> f64 {
    let n = u.len();
    let kk = k as f64;
    match degree {
        0 => u[n - 1],
        1 => u[n - 1] + kk * (u[n - 1] - u[n - 2]),
        2 => {
            (1.0 + 1.5 * kk + 0.5 * kk * kk) * u[n - 1]
                + (-2.0 * kk - kk * kk) * u[n - 2]
                + (0.5 * kk + 0.5 * kk * kk) * u[n - 3]
        }
        3 => {
            (1.0 + (11.0 / 6.0) * kk + kk * kk + (1.0 / 6.0) * kk * kk * kk) * u[n - 1]
                + (-3.0 * kk - 2.5 * kk * kk - 0.5 * kk * kk * kk) * u[n - 2]
                + (1.5 * kk + 2.0 * kk * kk + 0.5 * kk * kk * kk) * u[n - 3]
                + ((-1.0 / 3.0) * kk - 0.5 * kk * kk - (1.0 / 6.0) * kk * kk * kk) * u[n - 4]
        }
        _ => unreachable!("guarded by 0..=3 check above"),
    }
}

fn fill_ghosts_prescribed(u_ext: &mut [f64], ng: usize, prescribe: &dyn Fn(Side, usize) -> f64) {
    let n_interior = u_ext.len() - 2 * ng;
    for k in 1..=ng {
        u_ext[ng - k] = prescribe(Side::Left, k);
        u_ext[ng + n_interior + k - 1] = prescribe(Side::Right, k);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use serde_json::json;

    fn centered_fd_json() -> serde_json::Value {
        json!([
            {
                "selector": {"kind": "cartesian", "axis": "x", "offset": -1},
                "coeff": {"op": "/", "args": [-1, {"op": "*", "args": [2, "dx"]}]}
            },
            {
                "selector": {"kind": "cartesian", "axis": "x", "offset": 1},
                "coeff": {"op": "/", "args": [1, {"op": "*", "args": [2, "dx"]}]}
            }
        ])
    }

    fn dx_bindings(dx: f64) -> HashMap<String, f64> {
        let mut b = HashMap::new();
        b.insert("dx".to_string(), dx);
        b
    }

    #[test]
    fn periodic_kind_byte_equal_to_periodic_applier() {
        let n = 32usize;
        let dx = 1.0 / n as f64;
        let u: Vec<f64> = (1..=n)
            .map(|i| (2.0 * std::f64::consts::PI * (i as f64 - 0.5) * dx).sin())
            .collect();
        let bindings = dx_bindings(dx);
        let stencil = centered_fd_json();
        let reference = apply_stencil_periodic_1d(&stencil, &u, &bindings, None).unwrap();
        for ng in [1, 2, 5] {
            let policy = BoundaryPolicySpec::new(BoundaryPolicyKind::Periodic);
            let got = apply_stencil_ghosted_1d(&stencil, &u, &bindings, ng, &policy, None, None)
                .unwrap();
            assert_eq!(got, reference, "ghost_width={ng} periodic must be bit-equal");
        }
    }

    #[test]
    fn reflecting_zero_flux_at_boundary_on_symmetric_profile() {
        let n = 16usize;
        let dx = 1.0 / n as f64;
        let u: Vec<f64> = (1..=n)
            .map(|i| (std::f64::consts::PI * (i as f64 - 0.5) * dx).cos())
            .collect();
        let bindings = dx_bindings(dx);
        let stencil = centered_fd_json();
        let policy = BoundaryPolicySpec::new(BoundaryPolicyKind::Reflecting);
        let got =
            apply_stencil_ghosted_1d(&stencil, &u, &bindings, 1, &policy, None, None).unwrap();
        // First interior cell: ghost is u[0] (mirror), so the centered FD
        // there reduces to (u[1] - u[0]) / (2 dx).
        let expected_first = (u[1] - u[0]) / (2.0 * dx);
        let expected_last = (u[n - 1] - u[n - 2]) / (2.0 * dx);
        assert!((got[0] - expected_first).abs() < 1e-12);
        assert!((got[n - 1] - expected_last).abs() < 1e-12);
    }

    #[test]
    fn neumann_zero_alias_resolves_to_reflecting() {
        let n = 8usize;
        let dx = 0.1;
        let u: Vec<f64> = (1..=n).map(|i| i as f64).collect();
        let bindings = dx_bindings(dx);
        let stencil = centered_fd_json();
        let via_reflecting = apply_stencil_ghosted_1d(
            &stencil,
            &u,
            &bindings,
            1,
            &BoundaryPolicySpec::new(BoundaryPolicyKind::Reflecting),
            None,
            None,
        )
        .unwrap();
        let via_neumann = apply_stencil_ghosted_1d(
            &stencil,
            &u,
            &bindings,
            1,
            &BoundaryPolicySpec::new(BoundaryPolicyKind::NeumannZero),
            None,
            None,
        )
        .unwrap();
        assert_eq!(via_neumann, via_reflecting);
    }

    #[test]
    fn one_sided_linear_default_exact_on_linear_profile() {
        let n = 12usize;
        let dx = 0.1;
        let u: Vec<f64> = (1..=n).map(|i| 2.0 + 3.0 * i as f64).collect();
        let bindings = dx_bindings(dx);
        let stencil = centered_fd_json();
        let policy = BoundaryPolicySpec::new(BoundaryPolicyKind::OneSidedExtrapolation);
        let got =
            apply_stencil_ghosted_1d(&stencil, &u, &bindings, 1, &policy, None, None).unwrap();
        let expected = 3.0 / dx;
        for g in &got {
            assert!((g - expected).abs() < 1e-10, "got {g}, expected {expected}");
        }
    }

    #[test]
    fn one_sided_degree_two_exact_on_quadratic_profile() {
        let n = 10usize;
        let dx = 0.5;
        let u: Vec<f64> = (1..=n).map(|i| (i as f64).powi(2)).collect();
        let bindings = dx_bindings(dx);
        let stencil = centered_fd_json();
        let mut policy = BoundaryPolicySpec::new(BoundaryPolicyKind::OneSidedExtrapolation);
        policy.degree = Some(2);
        let got =
            apply_stencil_ghosted_1d(&stencil, &u, &bindings, 1, &policy, None, None).unwrap();
        // Centered FD on i^2: ((i+1)^2 - (i-1)^2)/(2 dx) = 2i/dx.
        for (idx, g) in got.iter().enumerate() {
            let i = (idx + 1) as f64;
            let expected = 2.0 * i / dx;
            assert!((g - expected).abs() < 1e-10);
        }
    }

    #[test]
    fn one_sided_degree_three_exact_on_cubic_profile() {
        let n = 12usize;
        let dx = 0.25;
        let u: Vec<f64> = (1..=n).map(|i| (i as f64).powi(3)).collect();
        let bindings = dx_bindings(dx);
        let stencil = centered_fd_json();
        let mut policy = BoundaryPolicySpec::new(BoundaryPolicyKind::OneSidedExtrapolation);
        policy.degree = Some(3);
        let got =
            apply_stencil_ghosted_1d(&stencil, &u, &bindings, 1, &policy, None, None).unwrap();
        // Centered FD on i^3: ((i+1)^3 - (i-1)^3)/(2 dx) = (6 i^2 + 2)/(2 dx).
        for (idx, g) in got.iter().enumerate() {
            let i = (idx + 1) as f64;
            let expected = (6.0 * i * i + 2.0) / (2.0 * dx);
            assert!((g - expected).abs() < 1e-10);
        }
    }

    #[test]
    fn extrapolate_alias_defaults_to_degree_one() {
        let n = 8usize;
        let dx = 0.1;
        let u: Vec<f64> = (1..=n).map(|i| 1.5 * i as f64 + 0.5).collect();
        let bindings = dx_bindings(dx);
        let stencil = centered_fd_json();
        let policy = BoundaryPolicySpec::new(BoundaryPolicyKind::Extrapolate);
        let got =
            apply_stencil_ghosted_1d(&stencil, &u, &bindings, 1, &policy, None, None).unwrap();
        let expected = 1.5 / dx;
        for g in &got {
            assert!((g - expected).abs() < 1e-10);
        }
    }

    #[test]
    fn prescribed_exact_on_linear_with_linear_ghost_supplier() {
        let n = 8usize;
        let dx = 0.1;
        let u: Vec<f64> = (1..=n).map(|i| i as f64).collect();
        let bindings = dx_bindings(dx);
        let stencil = centered_fd_json();
        let policy = BoundaryPolicySpec::new(BoundaryPolicyKind::Prescribed);
        let prescribe = |side: Side, k: usize| -> f64 {
            match side {
                Side::Left => 1.0 - k as f64,
                Side::Right => (n + k) as f64,
            }
        };
        let got = apply_stencil_ghosted_1d(
            &stencil,
            &u,
            &bindings,
            1,
            &policy,
            Some(&prescribe),
            None,
        )
        .unwrap();
        let expected = 1.0 / dx;
        for g in &got {
            assert!((g - expected).abs() < 1e-10);
        }
    }

    #[test]
    fn prescribed_alias_ghosted_requires_prescribe_callback() {
        let n = 8usize;
        let dx = 0.1;
        let u: Vec<f64> = (1..=n).map(|i| i as f64).collect();
        let bindings = dx_bindings(dx);
        let stencil = centered_fd_json();
        let policy = BoundaryPolicySpec::new(BoundaryPolicyKind::Ghosted);
        let err = apply_stencil_ghosted_1d(&stencil, &u, &bindings, 1, &policy, None, None)
            .unwrap_err();
        assert_eq!(err.code(), "E_MMS_BAD_FIXTURE");
    }

    #[test]
    fn ghost_width_too_small_for_stencil_offset_errors() {
        // 4th-order centered FD spans offsets ±2.
        let stencil = json!([
            {"selector": {"kind": "cartesian", "axis": "x", "offset": -2},
             "coeff": {"op": "/", "args": [1,  {"op": "*", "args": [12, "dx"]}]}},
            {"selector": {"kind": "cartesian", "axis": "x", "offset": -1},
             "coeff": {"op": "/", "args": [-8, {"op": "*", "args": [12, "dx"]}]}},
            {"selector": {"kind": "cartesian", "axis": "x", "offset": 1},
             "coeff": {"op": "/", "args": [8,  {"op": "*", "args": [12, "dx"]}]}},
            {"selector": {"kind": "cartesian", "axis": "x", "offset": 2},
             "coeff": {"op": "/", "args": [-1, {"op": "*", "args": [12, "dx"]}]}}
        ]);
        let n = 16usize;
        let dx = 1.0 / n as f64;
        let u: Vec<f64> = (1..=n)
            .map(|i| (2.0 * std::f64::consts::PI * (i as f64 - 0.5) * dx).sin())
            .collect();
        let bindings = dx_bindings(dx);
        let policy = BoundaryPolicySpec::new(BoundaryPolicyKind::Periodic);
        let err = apply_stencil_ghosted_1d(&stencil, &u, &bindings, 1, &policy, None, None)
            .unwrap_err();
        assert_eq!(err.code(), "E_GHOST_WIDTH_TOO_SMALL");
    }

    #[test]
    fn panel_dispatch_recognised_but_unsupported() {
        let n = 8usize;
        let dx = 0.1;
        let u: Vec<f64> = (1..=n).map(|i| i as f64).collect();
        let bindings = dx_bindings(dx);
        let stencil = centered_fd_json();
        let mut policy = BoundaryPolicySpec::new(BoundaryPolicyKind::PanelDispatch);
        policy.interior = Some("dist".to_string());
        policy.boundary = Some("dist_bnd".to_string());
        let err = apply_stencil_ghosted_1d(&stencil, &u, &bindings, 1, &policy, None, None)
            .unwrap_err();
        assert_eq!(err.code(), "E_GHOST_FILL_UNSUPPORTED");
    }

    #[test]
    fn periodic_applier_centered_fd_on_sin_is_close_to_analytic_cos() {
        // Sanity: the centered FD wrap matches Julia's apply_stencil_periodic_1d
        // numerical behaviour. Used by mms_convergence in the Julia path.
        let n = 64usize;
        let dx = 1.0 / n as f64;
        let u: Vec<f64> = (1..=n)
            .map(|i| (2.0 * std::f64::consts::PI * (i as f64 - 0.5) * dx).sin())
            .collect();
        let bindings = dx_bindings(dx);
        let stencil = centered_fd_json();
        let got = apply_stencil_periodic_1d(&stencil, &u, &bindings, None).unwrap();
        // Compare to 2π cos(2π x) at cell centers; centered FD is O(dx²)
        // accurate, so 1/n² ≈ 2.4e-4 — pick a generous tolerance.
        for (idx, g) in got.iter().enumerate() {
            let x = (idx as f64 + 0.5) * dx;
            let analytic = 2.0 * std::f64::consts::PI * (2.0 * std::f64::consts::PI * x).cos();
            assert!((g - analytic).abs() < 5e-2);
        }
    }

    #[test]
    fn multi_stencil_mapping_requires_sub_stencil_selector() {
        let stencil = json!({
            "left":  [{"selector": {"kind": "cartesian", "axis": "x", "offset": 0},
                       "coeff": 1.0}],
            "right": [{"selector": {"kind": "cartesian", "axis": "x", "offset": 0},
                       "coeff": 2.0}]
        });
        let u = vec![1.0_f64, 2.0, 3.0, 4.0];
        let bindings: HashMap<String, f64> = HashMap::new();
        let err =
            apply_stencil_periodic_1d(&stencil, &u, &bindings, None).unwrap_err();
        assert_eq!(err.code(), "E_MMS_BAD_FIXTURE");

        let got_left =
            apply_stencil_periodic_1d(&stencil, &u, &bindings, Some("left")).unwrap();
        let got_right =
            apply_stencil_periodic_1d(&stencil, &u, &bindings, Some("right")).unwrap();
        assert_eq!(got_left, vec![1.0, 2.0, 3.0, 4.0]);
        assert_eq!(got_right, vec![2.0, 4.0, 6.0, 8.0]);

        let err = apply_stencil_periodic_1d(&stencil, &u, &bindings, Some("missing")).unwrap_err();
        assert_eq!(err.code(), "E_MMS_BAD_FIXTURE");
    }

    #[test]
    fn list_form_rejects_sub_stencil_argument() {
        let stencil = centered_fd_json();
        let u = vec![1.0, 2.0, 3.0, 4.0];
        let bindings = dx_bindings(0.5);
        let err =
            apply_stencil_periodic_1d(&stencil, &u, &bindings, Some("any")).unwrap_err();
        assert_eq!(err.code(), "E_MMS_BAD_FIXTURE");
    }
}
