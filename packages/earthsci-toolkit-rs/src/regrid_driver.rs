//! C4 regrid driver — reproject + horizontal regrid + `lev=min` (bead
//! ess-14f.10), the Rust sibling of Python
//! `earthsci_toolkit.data_loaders.regrid_driver`.
//!
//! This is the ESS Rust-runtime orchestration that lands a data-loader field
//! onto a model's projected target domain grid. It consumes the EXISTING ESD
//! declarative rules numerically (it does not add an ESS primitive):
//!
//! 1. **Resolve the target grid.** A model `domain` (e.g. `camp_fire_surface`)
//!    gives a projected `(x, y)` lattice in metres plus a `spatial_ref` PROJ
//!    string. [`build_target_grid`] builds the lattice (`min + i·spacing` per
//!    dimension) and applies the ESD reprojection rule ([`crate::reproject`]) to
//!    get the lon/lat cell **centers** (for point/bspline sampling) and cell
//!    **corner rings** (for conservative overlap). The regridder bins by lon/lat,
//!    so the projected target is converted to lon/lat once and cached.
//! 2. **Reduce `lev=min` early.** A 3-D field (`lev, lat, lon`) collapses to the
//!    ground surface via [`lev_min_reduce`], the numeric image of the ESD
//!    `lev_min_surface_reduce` rule (keep the slice at the minimum `lev`).
//! 3. **Horizontal regrid per method.** [`regrid_field`] dispatches on the
//!    per-variable [`crate::types::RegridSpec`] `method` to a
//!    [`crate::regrid_kernels`] kernel — `bspline`, `conservative`, or
//!    `cell_average`.
//!
//! The output is a flat `f64` `Vec` in the target domain's spatial-dim order
//! (C-order), ready to bind into a simulation forcing buffer exactly where the
//! raw loader array would have gone (the R-1 provider seam consumes it).

use std::collections::HashMap;

use ndarray::{Array2, ArrayD, Axis};

use crate::geometry::Manifold;
use crate::regrid_kernels as k;
use crate::reproject::Reprojector;
use crate::types::Domain;

/// Raised when a loader field cannot be regridded onto the target domain.
/// Mirrors Python `RegridDriverError`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RegridDriverError {
    message: String,
}

impl RegridDriverError {
    pub(crate) fn new(message: impl Into<String>) -> Self {
        RegridDriverError {
            message: message.into(),
        }
    }

    /// The underlying failure reason.
    pub fn message(&self) -> &str {
        &self.message
    }
}

impl std::fmt::Display for RegridDriverError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "regrid driver error: {}", self.message)
    }
}

impl std::error::Error for RegridDriverError {}

impl From<crate::reproject::ReprojectError> for RegridDriverError {
    fn from(e: crate::reproject::ReprojectError) -> Self {
        RegridDriverError::new(e.message().to_string())
    }
}

impl From<k::RegridKernelError> for RegridDriverError {
    fn from(e: k::RegridKernelError) -> Self {
        RegridDriverError::new(e.message().to_string())
    }
}

// --------------------------------------------------------------------------
// Target grid construction
// --------------------------------------------------------------------------

/// One spatial dimension of a model domain: `[min, max]` in projected units with
/// a fixed `grid_spacing`. The `(dim_name, SpatialDim)` list passed to
/// [`build_target_grid`] mirrors a domain's `spatial` block.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct SpatialDim {
    /// Lower bound (projected units, e.g. metres).
    pub min: f64,
    /// Upper bound (projected units).
    pub max: f64,
    /// Cell spacing (projected units).
    pub grid_spacing: f64,
}

/// A model domain's grid expressed in lon/lat for regridding.
///
/// `dims` are the horizontal spatial dim names in domain order (e.g.
/// `["x", "y"]`); `shape` is the matching cell count per dim. `center_lon` /
/// `center_lat` are the reprojected cell centers, flattened C-order over `shape`
/// (cell `(i, j)` at flat index `i*shape[1]+j`). `corner_rings` holds one
/// `[4]`-vertex lon/lat ring per cell in the same C-order. Mirrors Python
/// `TargetGrid`.
#[derive(Debug, Clone)]
pub struct TargetGrid {
    /// Horizontal spatial dim names in domain order.
    pub dims: Vec<String>,
    /// Cell count per dim.
    pub shape: Vec<usize>,
    /// Per-dim projected node coordinates (the lattice before reprojection).
    pub centers: HashMap<String, Vec<f64>>,
    /// Reprojected cell-center longitudes, flat C-order over `shape`.
    pub center_lon: Vec<f64>,
    /// Reprojected cell-center latitudes, flat C-order over `shape`.
    pub center_lat: Vec<f64>,
    /// One CCW 4-vertex `(lon, lat)` corner ring per cell (empty for a 1-D grid).
    pub corner_rings: Vec<Vec<(f64, f64)>>,
}

/// Cell-center coordinates and spacing for one spatial dimension.
///
/// Node count follows `spatial_discretize` — `round((max−min)/spacing) + 1` —
/// so the lattice spans `[min, max]`. Mirrors Python `_dim_nodes`.
fn dim_nodes(spec: &SpatialDim) -> Result<(Vec<f64>, f64), RegridDriverError> {
    if !spec.grid_spacing.is_finite() || spec.grid_spacing <= 0.0 {
        return Err(RegridDriverError::new(
            "target domain dimension needs a positive grid_spacing",
        ));
    }
    let n = ((spec.max - spec.min) / spec.grid_spacing).round() as i64 + 1;
    if n < 1 {
        return Err(RegridDriverError::new(
            "target domain dimension has no cells",
        ));
    }
    let nodes: Vec<f64> = (0..n)
        .map(|i| spec.min + i as f64 * spec.grid_spacing)
        .collect();
    Ok((nodes, spec.grid_spacing))
}

/// Build a lon/lat [`TargetGrid`] from an ordered list of named spatial dims.
///
/// Supports a 2-D horizontal grid (the camp-fire `x`/`y` surface case); a 1-D
/// grid is also handled (no corner rings). The `spatial_ref` PROJ string drives
/// the projected→lon/lat conversion (`longlat` identity or spherical `lcc`).
/// Mirrors Python `build_target_grid` (which takes the domain object directly;
/// see [`build_target_grid_from_domain`] for that convenience).
pub fn build_target_grid(
    dims: &[(String, SpatialDim)],
    spatial_ref: Option<&str>,
) -> Result<TargetGrid, RegridDriverError> {
    if dims.is_empty() {
        return Err(RegridDriverError::new(
            "target domain has no spatial dimensions",
        ));
    }
    let reproj = Reprojector::from_spatial_ref(spatial_ref)?;

    let dim_names: Vec<String> = dims.iter().map(|(name, _)| name.clone()).collect();
    let mut centers: HashMap<String, Vec<f64>> = HashMap::new();
    let mut spacing: HashMap<String, f64> = HashMap::new();
    for (name, spec) in dims {
        let (nodes, sp) = dim_nodes(spec)?;
        centers.insert(name.clone(), nodes);
        spacing.insert(name.clone(), sp);
    }
    let shape: Vec<usize> = dim_names.iter().map(|d| centers[d].len()).collect();

    if dim_names.len() == 1 {
        let d0 = &dim_names[0];
        let (lon, lat): (Vec<f64>, Vec<f64>) = centers[d0]
            .iter()
            .map(|&x| reproj.xy_to_lonlat(x, 0.0))
            .unzip();
        return Ok(TargetGrid {
            dims: dim_names,
            shape,
            centers,
            center_lon: lon,
            center_lat: lat,
            corner_rings: Vec::new(),
        });
    }
    if dim_names.len() != 2 {
        return Err(RegridDriverError::new(format!(
            "target grid build supports 1-D or 2-D domains; got {} dims",
            dim_names.len()
        )));
    }

    let (d0, d1) = (dim_names[0].clone(), dim_names[1].clone());
    let h0 = spacing[&d0] / 2.0;
    let h1 = spacing[&d1] / 2.0;
    // Small node vectors (one per dim); clone so the lattice loops borrow neither
    // `centers` (moved into the result below) nor `dim_names`.
    let nodes0 = centers[&d0].clone();
    let nodes1 = centers[&d1].clone();
    let cap = nodes0.len() * nodes1.len();

    let mut center_lon = Vec::with_capacity(cap);
    let mut center_lat = Vec::with_capacity(cap);
    let mut corner_rings: Vec<Vec<(f64, f64)>> = Vec::with_capacity(cap);
    // Mesh in [d0, d1] order so flattening matches the C-order layout.
    for &x0 in &nodes0 {
        for &y0 in &nodes1 {
            let (clon, clat) = reproj.xy_to_lonlat(x0, y0);
            center_lon.push(clon);
            center_lat.push(clat);
            // Cell corner ring: each center ± half-spacing, reprojected, CCW.
            let corners = [
                (x0 - h0, y0 - h1),
                (x0 + h0, y0 - h1),
                (x0 + h0, y0 + h1),
                (x0 - h0, y0 + h1),
            ];
            corner_rings.push(
                corners
                    .iter()
                    .map(|&(x, y)| reproj.xy_to_lonlat(x, y))
                    .collect(),
            );
        }
    }
    Ok(TargetGrid {
        dims: dim_names,
        shape,
        centers,
        center_lon,
        center_lat,
        corner_rings,
    })
}

/// Build a [`TargetGrid`] from a model [`Domain`] (the convenience the R-1 seam
/// uses). Parses `domain.spatial` (a `{dim: {min, max, grid_spacing}}` object)
/// and `domain.spatial_ref`. Dimensions are taken in the JSON object's key order
/// (alphabetical, as `serde_json` does not preserve insertion order); for the
/// camp-fire `x`/`y` surface this is the natural order. A non-alphabetical dim
/// order must use [`build_target_grid`] with an explicit list.
pub fn build_target_grid_from_domain(domain: &Domain) -> Result<TargetGrid, RegridDriverError> {
    let spatial = domain
        .spatial
        .as_ref()
        .and_then(|v| v.as_object())
        .ok_or_else(|| RegridDriverError::new("target domain has no spatial dimensions"))?;
    let mut dims: Vec<(String, SpatialDim)> = Vec::with_capacity(spatial.len());
    for (name, spec) in spatial.iter() {
        let obj = spec.as_object().ok_or_else(|| {
            RegridDriverError::new(format!("spatial dimension {name:?} is not an object"))
        })?;
        let get = |key: &str| -> Result<f64, RegridDriverError> {
            obj.get(key).and_then(|v| v.as_f64()).ok_or_else(|| {
                RegridDriverError::new(format!("dimension {name:?} needs numeric {key}"))
            })
        };
        dims.push((
            name.clone(),
            SpatialDim {
                min: get("min")?,
                max: get("max")?,
                grid_spacing: get("grid_spacing")?,
            },
        ));
    }
    build_target_grid(&dims, domain.spatial_ref.as_deref())
}

// --------------------------------------------------------------------------
// lev=min surface reduction (ESD lev_min_surface_reduce rule)
// --------------------------------------------------------------------------

/// Collapse an N-D field to the surface by keeping the minimum-`lev` slice.
///
/// `lev_coord` are the vertical coordinate values; the slice at
/// `argmin(lev_coord)` along `lev_axis` is returned (the numeric image of the ESD
/// `lev_min_surface_reduce` value-at-argmin rule). The first minimum wins (numpy
/// `argmin` semantics). Mirrors Python `lev_min_reduce`.
pub fn lev_min_reduce(
    field: &ArrayD<f64>,
    lev_coord: &[f64],
    lev_axis: usize,
) -> Result<ArrayD<f64>, RegridDriverError> {
    if lev_axis >= field.ndim() {
        return Err(RegridDriverError::new(format!(
            "lev_axis {lev_axis} out of range for {}-D field",
            field.ndim()
        )));
    }
    if field.shape()[lev_axis] != lev_coord.len() {
        return Err(RegridDriverError::new(format!(
            "lev axis size {} != lev_coord size {}",
            field.shape()[lev_axis],
            lev_coord.len()
        )));
    }
    if lev_coord.is_empty() {
        return Err(RegridDriverError::new("lev_coord is empty"));
    }
    // First index of the minimum (numpy argmin: strict `<` keeps the first).
    let mut k = 0usize;
    let mut best = lev_coord[0];
    for (i, &v) in lev_coord.iter().enumerate() {
        if v < best {
            best = v;
            k = i;
        }
    }
    Ok(field.index_axis(Axis(lev_axis), k).to_owned())
}

// --------------------------------------------------------------------------
// Source-cell rings (separable lat/lon grid -> per-cell corner polygons)
// --------------------------------------------------------------------------

/// Cell edges (`n+1`) bracketing `n` ascending centers (midpoint split, the two
/// ends reflected). Mirrors Python `_edges_from_centers`.
fn edges_from_centers(centers: &[f64]) -> Vec<f64> {
    let n = centers.len();
    if n == 0 {
        return Vec::new();
    }
    if n == 1 {
        return vec![centers[0] - 0.5, centers[0] + 0.5];
    }
    let mut edges = Vec::with_capacity(n + 1);
    let first_mid = (centers[0] + centers[1]) / 2.0;
    edges.push(centers[0] - (first_mid - centers[0]));
    for w in centers.windows(2) {
        edges.push((w[0] + w[1]) / 2.0);
    }
    let last_mid = (centers[n - 2] + centers[n - 1]) / 2.0;
    edges.push(centers[n - 1] + (centers[n - 1] - last_mid));
    edges
}

/// One CCW 4-vertex `(lon, lat)` ring per source cell, flattened `[lat, lon]`
/// C-order (cell `(a, b)` at flat `a*nlon+b`). Mirrors Python `_source_cell_rings`.
fn source_cell_rings(src_lon: &[f64], src_lat: &[f64]) -> Vec<Vec<(f64, f64)>> {
    let lon_e = edges_from_centers(src_lon);
    let lat_e = edges_from_centers(src_lat);
    let mut rings = Vec::with_capacity(src_lat.len() * src_lon.len());
    for a in 0..src_lat.len() {
        let (y0, y1) = (lat_e[a], lat_e[a + 1]);
        for b in 0..src_lon.len() {
            let (x0, x1) = (lon_e[b], lon_e[b + 1]);
            rings.push(vec![(x0, y0), (x1, y0), (x1, y1), (x0, y1)]);
        }
    }
    rings
}

// --------------------------------------------------------------------------
// Horizontal regrid dispatch
// --------------------------------------------------------------------------

/// Regrid a 2-D `(lat, lon)` source field onto `target` by `method`.
///
/// Returns a flat array in the target's C-order cell layout. `bspline` samples
/// the source grid bilinearly at each target center; `conservative` performs an
/// overlap-area remap of source cells onto the target corner rings;
/// `cell_average` bins the source nodes (treated as scattered points) into the
/// target cells. Mirrors Python `regrid_field`.
#[allow(clippy::too_many_arguments)]
pub fn regrid_field(
    field_2d: &Array2<f64>,
    src_lon: &[f64],
    src_lat: &[f64],
    target: &TargetGrid,
    method: &str,
    manifold: Manifold,
    missing_value: f64,
    atol: f64,
) -> Result<Vec<f64>, RegridDriverError> {
    let (nlat, nlon) = (src_lat.len(), src_lon.len());
    if field_2d.shape() != [nlat, nlon] {
        return Err(RegridDriverError::new(format!(
            "source field shape {:?} != (nlat={nlat}, nlon={nlon})",
            field_2d.shape()
        )));
    }
    match method {
        "bspline" => {
            // Degree-1 tensor sampling: locate each target center in the source
            // grid and bilinearly blend (the BSplineRegridBilinear2D image).
            // F_src is indexed [lon_index, lat_index] to match the kernel layout.
            let (base_x, s_x) = k::locate_1d(&target.center_lon, src_lon, true)?;
            let (base_y, s_y) = k::locate_1d(&target.center_lat, src_lat, true)?;
            let f_xy = field_2d.t().to_owned(); // (nlon, nlat)
            Ok(k::bspline_regrid_bilinear_2d(
                &f_xy, &base_x, &base_y, &s_x, &s_y,
            ))
        }
        "conservative" => {
            let src_rings = source_cell_rings(src_lon, src_lat);
            // field [lat, lon] C-order matches source_cell_rings order.
            let f_src: Vec<f64> = field_2d.iter().copied().collect();
            let (f_tgt, _a, _aj) =
                k::conservative_regrid(&f_src, &src_rings, &target.corner_rings, manifold, atol)?;
            Ok(f_tgt)
        }
        "cell_average" => {
            // Source nodes as scattered points: station (a, b) has lon=src_lon[b],
            // lat=src_lat[a], value=field[a, b] (C-order over [lat, lon]).
            let mut s_lon = Vec::with_capacity(nlat * nlon);
            let mut s_lat = Vec::with_capacity(nlat * nlon);
            for &lat in src_lat {
                for &lon in src_lon {
                    s_lon.push(lon);
                    s_lat.push(lat);
                }
            }
            let f_src: Vec<f64> = field_2d.iter().copied().collect();
            let dx = min_unique_spacing(&target.center_lon);
            let dy = min_unique_spacing(&target.center_lat);
            Ok(k::cell_average_regrid(
                &f_src,
                &s_lon,
                &s_lat,
                &target.center_lon,
                &target.center_lat,
                dx,
                dy,
                missing_value,
            ))
        }
        other => Err(RegridDriverError::new(format!(
            "unknown regrid method {other:?}; expected bspline|conservative|cell_average"
        ))),
    }
}

/// Smallest gap between distinct values (rounded to 9 decimals), or `1.0` for a
/// single value — the `cell_average` target bin size. Mirrors Python's
/// `min(diff(unique(round(coords, 9))))` heuristic.
fn min_unique_spacing(vals: &[f64]) -> f64 {
    if vals.len() <= 1 {
        return 1.0;
    }
    let mut rounded: Vec<f64> = vals.iter().map(|&v| (v * 1e9).round() / 1e9).collect();
    rounded.sort_by(|a, b| a.partial_cmp(b).unwrap());
    rounded.dedup();
    if rounded.len() <= 1 {
        return 1.0;
    }
    rounded
        .windows(2)
        .map(|w| w[1] - w[0])
        .fold(f64::INFINITY, f64::min)
}

/// Full per-field pipeline: `lev=min` (if 3-D) → horizontal regrid → flat.
///
/// `values` is the raw loaded field. When `lev_coord` is given the field is first
/// collapsed to the surface, then regridded onto `target` by `method`. Mirrors
/// Python `regrid_loader_field`.
#[allow(clippy::too_many_arguments)]
pub fn regrid_loader_field(
    values: &ArrayD<f64>,
    src_lon: &[f64],
    src_lat: &[f64],
    target: &TargetGrid,
    method: &str,
    lev_coord: Option<&[f64]>,
    lev_axis: usize,
    manifold: Manifold,
    missing_value: f64,
    atol: f64,
) -> Result<Vec<f64>, RegridDriverError> {
    let reduced;
    let arr: &ArrayD<f64> = match lev_coord {
        Some(lev) => {
            reduced = lev_min_reduce(values, lev, lev_axis)?;
            &reduced
        }
        None => values,
    };
    if arr.ndim() != 2 {
        return Err(RegridDriverError::new(format!(
            "regrid expects a 2-D field after lev reduction; got ndim={}",
            arr.ndim()
        )));
    }
    let field_2d = arr
        .view()
        .into_dimensionality::<ndarray::Ix2>()
        .map_err(|e| RegridDriverError::new(e.to_string()))?
        .to_owned();
    regrid_field(
        &field_2d,
        src_lon,
        src_lat,
        target,
        method,
        manifold,
        missing_value,
        atol,
    )
}

#[cfg(all(test, not(target_arch = "wasm32")))]
mod tests {
    use super::*;
    use ndarray::Array;

    const CAMPFIRE_SR: &str = "+proj=lcc +lat_1=30.0 +lat_2=60.0 +lat_0=39.0 +lon_0=-97.0 \
         +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs";

    fn campfire_dims() -> Vec<(String, SpatialDim)> {
        vec![
            (
                "x".to_string(),
                SpatialDim {
                    min: -2_026_020.2,
                    max: -1_990_020.2,
                    grid_spacing: 2000.0,
                },
            ),
            (
                "y".to_string(),
                SpatialDim {
                    min: 374_725.0,
                    max: 414_725.0,
                    grid_spacing: 2000.0,
                },
            ),
        ]
    }

    fn linspace(a: f64, b: f64, n: usize) -> Vec<f64> {
        if n == 1 {
            return vec![a];
        }
        let step = (b - a) / (n - 1) as f64;
        (0..n).map(|i| a + step * i as f64).collect()
    }

    #[test]
    fn build_target_grid_campfire_surface() {
        let tg = build_target_grid(&campfire_dims(), Some(CAMPFIRE_SR)).unwrap();
        assert_eq!(tg.dims, vec!["x".to_string(), "y".to_string()]);
        assert_eq!(tg.shape, vec![19, 21]);
        assert_eq!(tg.corner_rings.len(), 19 * 21);
        assert_eq!(tg.corner_rings[0].len(), 4);
        let lon_min = tg.center_lon.iter().cloned().fold(f64::INFINITY, f64::min);
        let lon_max = tg
            .center_lon
            .iter()
            .cloned()
            .fold(f64::NEG_INFINITY, f64::max);
        let lat_min = tg.center_lat.iter().cloned().fold(f64::INFINITY, f64::min);
        let lat_max = tg
            .center_lat
            .iter()
            .cloned()
            .fold(f64::NEG_INFINITY, f64::max);
        assert!(
            -122.0 < lon_min && lon_max < -121.0,
            "lon [{lon_min}, {lon_max}]"
        );
        assert!(
            39.0 < lat_min && lat_max < 40.5,
            "lat [{lat_min}, {lat_max}]"
        );
    }

    #[test]
    fn build_target_grid_from_domain_matches_explicit() {
        let domain: Domain = serde_json::from_value(serde_json::json!({
            "spatial": {
                "x": {"min": -2026020.2, "max": -1990020.2, "grid_spacing": 2000.0},
                "y": {"min": 374725.0, "max": 414725.0, "grid_spacing": 2000.0},
            },
            "spatial_ref": CAMPFIRE_SR,
        }))
        .unwrap();
        let tg = build_target_grid_from_domain(&domain).unwrap();
        let explicit = build_target_grid(&campfire_dims(), Some(CAMPFIRE_SR)).unwrap();
        assert_eq!(tg.shape, explicit.shape);
        assert_eq!(tg.center_lon, explicit.center_lon);
        assert_eq!(tg.center_lat, explicit.center_lat);
    }

    /// A field linear in lon/lat is reproduced exactly by bilinear sampling.
    fn linear_source(src_lon: &[f64], src_lat: &[f64]) -> Array2<f64> {
        let (nlat, nlon) = (src_lat.len(), src_lon.len());
        Array::from_shape_fn((nlat, nlon), |(a, b)| 2.0 * src_lon[b] + 3.0 * src_lat[a])
    }

    #[test]
    fn regrid_pipeline_bspline_linear_exact() {
        let tg = build_target_grid(&campfire_dims(), Some(CAMPFIRE_SR)).unwrap();
        let lon_min = tg.center_lon.iter().cloned().fold(f64::INFINITY, f64::min);
        let lon_max = tg
            .center_lon
            .iter()
            .cloned()
            .fold(f64::NEG_INFINITY, f64::max);
        let lat_min = tg.center_lat.iter().cloned().fold(f64::INFINITY, f64::min);
        let lat_max = tg
            .center_lat
            .iter()
            .cloned()
            .fold(f64::NEG_INFINITY, f64::max);
        let src_lon = linspace(lon_min - 0.1, lon_max + 0.1, 6);
        let src_lat = linspace(lat_min - 0.1, lat_max + 0.1, 5);
        let field = linear_source(&src_lon, &src_lat);
        let out = regrid_field(
            &field,
            &src_lon,
            &src_lat,
            &tg,
            "bspline",
            Manifold::Planar,
            f64::NAN,
            0.0,
        )
        .unwrap();
        assert_eq!(out.len(), tg.center_lon.len());
        for (k, &o) in out.iter().enumerate() {
            let want = 2.0 * tg.center_lon[k] + 3.0 * tg.center_lat[k];
            assert!((o - want).abs() < 1e-9, "cell {k}: {o} vs {want}");
        }
    }

    #[test]
    fn regrid_pipeline_3d_levmin_then_bspline() {
        let tg = build_target_grid(&campfire_dims(), Some(CAMPFIRE_SR)).unwrap();
        let lon_min = tg.center_lon.iter().cloned().fold(f64::INFINITY, f64::min);
        let lon_max = tg
            .center_lon
            .iter()
            .cloned()
            .fold(f64::NEG_INFINITY, f64::max);
        let lat_min = tg.center_lat.iter().cloned().fold(f64::INFINITY, f64::min);
        let lat_max = tg
            .center_lat
            .iter()
            .cloned()
            .fold(f64::NEG_INFINITY, f64::max);
        let src_lon = linspace(lon_min - 0.1, lon_max + 0.1, 6);
        let src_lat = linspace(lat_min - 0.1, lat_max + 0.1, 5);
        let base = linear_source(&src_lon, &src_lat); // surface slice (lev index 0)
        let (nlat, nlon) = (src_lat.len(), src_lon.len());
        // (lev=3, lat, lon) ascending lev; surface (min lev) is slice 0 == base.
        let f3 = Array::from_shape_fn(ndarray::IxDyn(&[3, nlat, nlon]), |idx| {
            base[[idx[1], idx[2]]] + 100.0 * idx[0] as f64
        });
        let out = regrid_loader_field(
            &f3,
            &src_lon,
            &src_lat,
            &tg,
            "bspline",
            Some(&[1.0, 2.0, 3.0]),
            0,
            Manifold::Planar,
            f64::NAN,
            0.0,
        )
        .unwrap();
        for (k, &o) in out.iter().enumerate() {
            let want = 2.0 * tg.center_lon[k] + 3.0 * tg.center_lat[k];
            assert!((o - want).abs() < 1e-9, "cell {k}: {o} vs {want}");
        }
    }

    #[test]
    fn regrid_pipeline_conservative_preserves_constant() {
        let tg = build_target_grid(&campfire_dims(), Some(CAMPFIRE_SR)).unwrap();
        let lon_min = tg.center_lon.iter().cloned().fold(f64::INFINITY, f64::min);
        let lon_max = tg
            .center_lon
            .iter()
            .cloned()
            .fold(f64::NEG_INFINITY, f64::max);
        let lat_min = tg.center_lat.iter().cloned().fold(f64::INFINITY, f64::min);
        let lat_max = tg
            .center_lat
            .iter()
            .cloned()
            .fold(f64::NEG_INFINITY, f64::max);
        let src_lon = linspace(lon_min - 0.1, lon_max + 0.1, 6);
        let src_lat = linspace(lat_min - 0.1, lat_max + 0.1, 5);
        let field = Array2::from_elem((src_lat.len(), src_lon.len()), 288.0);
        let out = regrid_field(
            &field,
            &src_lon,
            &src_lat,
            &tg,
            "conservative",
            Manifold::Planar,
            f64::NAN,
            0.0,
        )
        .unwrap();
        let covered: Vec<f64> = out.iter().cloned().filter(|&v| v != 0.0).collect();
        assert_eq!(covered.len(), out.len(), "every target cell covered");
        for v in covered {
            assert!((v - 288.0).abs() < 1e-9, "constant preserved: {v}");
        }
    }

    #[test]
    fn lev_min_golden() {
        // (x, y, lev), reduce on the lev axis (2); min lev value 1.0 is at index 1.
        let f3 = Array::from_shape_vec(
            ndarray::IxDyn(&[2, 2, 3]),
            vec![
                111.0, 112.0, 113.0, 121.0, 122.0, 123.0, //
                211.0, 212.0, 213.0, 221.0, 222.0, 223.0,
            ],
        )
        .unwrap();
        let surf = lev_min_reduce(&f3, &[3.0, 1.0, 2.0], 2).unwrap();
        assert_eq!(surf.shape(), [2, 2]);
        assert_eq!(surf[[0, 0]], 112.0);
        assert_eq!(surf[[0, 1]], 122.0);
        assert_eq!(surf[[1, 0]], 212.0);
        assert_eq!(surf[[1, 1]], 222.0);
    }

    #[test]
    fn edges_from_centers_reflects_ends() {
        let e = edges_from_centers(&[0.0, 1.0, 2.0, 3.0]);
        assert_eq!(e, vec![-0.5, 0.5, 1.5, 2.5, 3.5]);
    }
}
