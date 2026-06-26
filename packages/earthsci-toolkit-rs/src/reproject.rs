//! Coordinate reprojection for the C4 regrid bridge (bead ess-14f.10).
//!
//! The horizontal regridder ([`crate::regrid_driver`]) bins source and target
//! cells by **lon/lat**: it is CRS-agnostic and consumes geometry already in a
//! shared geographic frame. A *projected* target domain (e.g. a Lambert
//! Conformal Conic `camp_fire_surface` grid in metres) must therefore have its
//! `(x, y)` lattice converted to `(lon, lat)` before regridding.
//!
//! This module supplies that conversion, mirroring the ESD reprojection rules
//! (`reprojection/longlat.esm` identity and `reprojection/lambert_conformal.esm`
//! / the `lambert_conformal_construction` corner inverse) and the Python
//! `earthsci_toolkit.data_loaders.reproject` driver byte-for-byte. Both are
//! **spherical** closed-form transforms (Snyder, *Map Projections — A Working
//! Manual*, USGS PP 1395, §15) built from elementary ops — no PROJ runtime
//! dependency. The supported projections match the `GridCRS.projection` enum
//! that has a backing rule today: `longlat` and `lambert_conformal`. Other CRS
//! values (`mercator`, `polar_stereographic`, `rotated_pole`) have no ESD rule
//! yet and raise.
//!
//! The transforms are spherical; a `+datum=WGS84` domain carries no radius, so a
//! spherical Earth radius is assumed ([`DEFAULT_SPHERE_RADIUS_M`]). The
//! forward/inverse pair is self-consistent for any radius, so the projected
//! `(x, y)` lattice round-trips exactly regardless of the assumed `R`.

use std::collections::HashMap;

/// Spherical Earth radius assumed for a `+datum=WGS84` / unspecified-radius
/// projected CRS. 6 370 997 m (the WGS84 authalic radius used across
/// atmospheric-model LCC grids). Only affects absolute scale, never the
/// forward∘inverse round-trip. Matches Python `DEFAULT_SPHERE_RADIUS_M`.
pub const DEFAULT_SPHERE_RADIUS_M: f64 = 6_370_997.0;

/// `π/180` — the degrees→radians factor, written explicitly (rather than
/// [`f64::to_radians`]) so the arithmetic is bit-identical to the Python driver
/// and the `area_faq` unit-vector conversion.
const DEG2RAD: f64 = std::f64::consts::PI / 180.0;
/// `180/π` — the radians→degrees factor, explicit for the same parity reason.
const RAD2DEG: f64 = 180.0 / std::f64::consts::PI;

/// Raised when a CRS cannot be reprojected to lon/lat (an unsupported `+proj`,
/// a missing standard parallel, or a degenerate cone). Mirrors Python
/// `ReprojectionError`.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReprojectError {
    message: String,
}

impl ReprojectError {
    pub(crate) fn new(message: impl Into<String>) -> Self {
        ReprojectError {
            message: message.into(),
        }
    }

    /// The underlying failure reason.
    pub fn message(&self) -> &str {
        &self.message
    }
}

impl std::fmt::Display for ReprojectError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "reprojection error: {}", self.message)
    }
}

impl std::error::Error for ReprojectError {}

/// A parsed PROJ.4 token value. A `+key=value` token becomes [`ProjValue::Number`]
/// when `value` parses as `f64`, else [`ProjValue::Text`]; a bare `+flag` token
/// becomes [`ProjValue::Flag`]. Mirrors the mixed `float | str | True` dict
/// Python's `parse_proj_string` returns.
#[derive(Debug, Clone, PartialEq)]
pub enum ProjValue {
    /// A numeric parameter (e.g. `+lat_1=30.0`).
    Number(f64),
    /// A non-numeric parameter (e.g. `+proj=lcc`, `+units=m`).
    Text(String),
    /// A bare flag (e.g. `+no_defs`).
    Flag,
}

/// Parse a PROJ.4 `spatial_ref` string into a parameter map.
///
/// Handles the `+key=value` / bare `+flag` token grammar (e.g.
/// `"+proj=lcc +lat_1=30.0 +lat_2=60.0 +lat_0=39.0 +lon_0=-97.0 +datum=WGS84
/// +units=m +no_defs"`). Numeric values become [`ProjValue::Number`]; everything
/// else stays [`ProjValue::Text`]; bare flags map to [`ProjValue::Flag`].
/// Mirrors Python `parse_proj_string`.
pub fn parse_proj_string(spatial_ref: &str) -> HashMap<String, ProjValue> {
    let mut out: HashMap<String, ProjValue> = HashMap::new();
    for token in spatial_ref.split_whitespace() {
        let Some(body) = token.strip_prefix('+') else {
            continue;
        };
        match body.split_once('=') {
            Some((key, value)) => {
                let pv = match value.parse::<f64>() {
                    Ok(f) => ProjValue::Number(f),
                    Err(_) => ProjValue::Text(value.to_string()),
                };
                out.insert(key.to_string(), pv);
            }
            None => {
                if !body.is_empty() {
                    out.insert(body.to_string(), ProjValue::Flag);
                }
            }
        }
    }
    out
}

/// Numeric parameter lookup — `Some(f)` only when `key` is a [`ProjValue::Number`].
pub fn proj_number(params: &HashMap<String, ProjValue>, key: &str) -> Option<f64> {
    match params.get(key) {
        Some(ProjValue::Number(f)) => Some(*f),
        _ => None,
    }
}

/// String parameter lookup — `Some(s)` only when `key` is a [`ProjValue::Text`].
pub fn proj_text<'a>(params: &'a HashMap<String, ProjValue>, key: &str) -> Option<&'a str> {
    match params.get(key) {
        Some(ProjValue::Text(s)) => Some(s.as_str()),
        _ => None,
    }
}

/// Resolve the spherical radius from a parsed PROJ param map: `+R`, else `+a`,
/// else [`DEFAULT_SPHERE_RADIUS_M`]. Mirrors Python `_sphere_radius`.
fn sphere_radius(params: &HashMap<String, ProjValue>) -> f64 {
    proj_number(params, "R")
        .or_else(|| proj_number(params, "a"))
        .unwrap_or(DEFAULT_SPHERE_RADIUS_M)
}

/// Snyder LCC cone constants derived from a parsed CRS param map — the
/// reusable core of `reprojection/lambert_conformal.esm`. Holding the cone lets
/// a whole lattice be transformed without re-deriving the (trig-heavy)
/// constants per point.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct LccCone {
    /// Cone constant `n` (sine of the standard parallel in the tangent limit).
    pub n: f64,
    /// Radius scale `RF = R·F`.
    pub rf: f64,
    /// Latitude-of-origin polar distance `ρ0`.
    pub rho0: f64,
    /// Central meridian `+lon_0` (degrees).
    pub lon_0: f64,
    /// Spherical radius `R` (metres).
    pub radius: f64,
}

/// Build the [`LccCone`] from a parsed CRS param map.
///
/// Reproduces `reprojection/lambert_conformal.esm`: the standard-parallel cone
/// constant `n` (with the tangent-cone `lat_1 == lat_2` limit), the radius scale
/// `RF = R·F` and the latitude-of-origin polar distance `ρ0`. `lat_*` are
/// degrees; `lat_2`/`lat_0` default to `lat_1`, `lon_0` defaults to `0`. Mirrors
/// Python `_lcc_cone`.
pub fn lcc_cone(params: &HashMap<String, ProjValue>) -> Result<LccCone, ReprojectError> {
    let lat_1 = proj_number(params, "lat_1")
        .ok_or_else(|| ReprojectError::new("lambert_conformal CRS requires +lat_1"))?;
    let lat_2 = proj_number(params, "lat_2").unwrap_or(lat_1);
    let lat_0 = proj_number(params, "lat_0").unwrap_or(lat_1);
    let lon_0 = proj_number(params, "lon_0").unwrap_or(0.0);
    let radius = sphere_radius(params);

    let phi1 = lat_1 * DEG2RAD;
    let phi2 = lat_2 * DEG2RAD;
    let phi0 = lat_0 * DEG2RAD;
    let t1 = (std::f64::consts::FRAC_PI_4 + phi1 / 2.0).tan();
    let t2 = (std::f64::consts::FRAC_PI_4 + phi2 / 2.0).tan();
    let t0 = (std::f64::consts::FRAC_PI_4 + phi0 / 2.0).tan();
    let n = if (phi1 - phi2).abs() < 1e-12 {
        phi1.sin()
    } else {
        (phi1.cos() / phi2.cos()).ln() / (t2 / t1).ln()
    };
    if n == 0.0 {
        return Err(ReprojectError::new("degenerate LCC cone constant n == 0"));
    }
    let big_f = phi1.cos() * t1.powf(n) / n;
    let rf = radius * big_f;
    let rho0 = rf / t0.powf(n);
    Ok(LccCone {
        n,
        rf,
        rho0,
        lon_0,
        radius,
    })
}

/// Spherical LCC forward over a precomputed [`LccCone`]: `(lon, lat)` degrees →
/// projected `(x, y)` metres.
pub fn lcc_forward_cone(lon: f64, lat: f64, cone: &LccCone) -> (f64, f64) {
    let phi = lat * DEG2RAD;
    let tphi = (std::f64::consts::FRAC_PI_4 + phi / 2.0).tan();
    let rho = cone.rf / tphi.powf(cone.n);
    let theta = cone.n * ((lon - cone.lon_0) * DEG2RAD);
    let x = rho * theta.sin();
    let y = cone.rho0 - rho * theta.cos();
    (x, y)
}

/// Spherical LCC inverse over a precomputed [`LccCone`]: projected `(x, y)`
/// metres → `(lon, lat)` degrees. Closed form (Snyder 15-5/15-7/15-8/15-9),
/// matching the `lambert_conformal_construction` corner inverse rule.
pub fn lcc_inverse_cone(x: f64, y: f64, cone: &LccCone) -> (f64, f64) {
    let rho0_my = cone.rho0 - y;
    let rho_inv = 1.0_f64.copysign(cone.n) * (x * x + rho0_my * rho0_my).sqrt();
    let theta_inv = x.atan2(rho0_my);
    let lon = cone.lon_0 + (theta_inv / cone.n) * RAD2DEG;
    let lat = (2.0 * (cone.rf / rho_inv).powf(1.0 / cone.n).atan() - std::f64::consts::FRAC_PI_2)
        * RAD2DEG;
    (lon, lat)
}

/// Spherical LCC forward from a parsed param map (builds the cone): `(lon, lat)`
/// degrees → projected `(x, y)` metres. Mirrors Python `lcc_forward`.
pub fn lcc_forward(
    lon: f64,
    lat: f64,
    params: &HashMap<String, ProjValue>,
) -> Result<(f64, f64), ReprojectError> {
    Ok(lcc_forward_cone(lon, lat, &lcc_cone(params)?))
}

/// Spherical LCC inverse from a parsed param map (builds the cone): projected
/// `(x, y)` metres → `(lon, lat)` degrees. Mirrors Python `lcc_inverse`.
pub fn lcc_inverse(
    x: f64,
    y: f64,
    params: &HashMap<String, ProjValue>,
) -> Result<(f64, f64), ReprojectError> {
    Ok(lcc_inverse_cone(x, y, &lcc_cone(params)?))
}

/// A resolved projected→geographic transform, built once from a `spatial_ref`
/// and applied per lattice point. The efficient core of the driver: a
/// `+proj=lcc` domain derives its (trig-heavy) [`LccCone`] a single time here
/// rather than re-parsing/re-deriving for every cell corner.
#[derive(Debug, Clone)]
pub enum Reprojector {
    /// `+proj=longlat` (or a missing/empty `spatial_ref`): the lattice is already
    /// geographic, so `(lon, lat) = (x, y)`.
    Identity,
    /// `+proj=lcc`: apply the spherical LCC inverse with this cone.
    Lcc(LccCone),
}

impl Reprojector {
    /// Resolve the transform for a domain `spatial_ref` PROJ string.
    ///
    /// `None`/empty and `+proj=longlat` (and its `latlong`/`lonlat` spellings)
    /// give [`Reprojector::Identity`]; `+proj=lcc` derives an [`LccCone`]. Any
    /// other projection has no backing reproject rule and raises. Mirrors the
    /// dispatch of Python `reproject_xy_to_lonlat`.
    pub fn from_spatial_ref(spatial_ref: Option<&str>) -> Result<Reprojector, ReprojectError> {
        let sr = match spatial_ref {
            Some(s) if !s.is_empty() => s,
            _ => return Ok(Reprojector::Identity),
        };
        let params = parse_proj_string(sr);
        let proj = proj_text(&params, "proj").unwrap_or("longlat");
        match proj {
            "longlat" | "latlong" | "lonlat" => Ok(Reprojector::Identity),
            "lcc" => Ok(Reprojector::Lcc(lcc_cone(&params)?)),
            other => Err(ReprojectError::new(format!(
                "no reprojection rule for +proj={other:?}; supported: longlat, lcc"
            ))),
        }
    }

    /// Convert one projected `(x, y)` point to `(lon, lat)` under this transform.
    pub fn xy_to_lonlat(&self, x: f64, y: f64) -> (f64, f64) {
        match self {
            Reprojector::Identity => (x, y),
            Reprojector::Lcc(cone) => lcc_inverse_cone(x, y, cone),
        }
    }
}

/// Convert a single projected `(x, y)` point to `(lon, lat)` per `spatial_ref`.
///
/// `+proj=longlat` (and a missing/empty `spatial_ref`) is the identity; `+proj=lcc`
/// applies the spherical LCC inverse; any other projection raises. Mirrors Python
/// `reproject_xy_to_lonlat` (scalar). Callers transforming a whole lattice should
/// build a [`Reprojector`] once and reuse it.
pub fn reproject_xy_to_lonlat(
    x: f64,
    y: f64,
    spatial_ref: Option<&str>,
) -> Result<(f64, f64), ReprojectError> {
    Ok(Reprojector::from_spatial_ref(spatial_ref)?.xy_to_lonlat(x, y))
}

#[cfg(test)]
mod tests {
    use super::*;

    const CAMPFIRE_SR: &str = "+proj=lcc +lat_1=30.0 +lat_2=60.0 +lat_0=39.0 +lon_0=-97.0 \
         +x_0=0 +y_0=0 +datum=WGS84 +units=m +no_defs";

    /// WRF cone params (note `lat_0 = 38.999996`, distinct from `CAMPFIRE_SR`),
    /// matching the Python `_WRF` corner-golden parameterization.
    fn wrf_params() -> HashMap<String, ProjValue> {
        HashMap::from([
            ("lat_1".to_string(), ProjValue::Number(30.0)),
            ("lat_2".to_string(), ProjValue::Number(60.0)),
            ("lat_0".to_string(), ProjValue::Number(38.999996)),
            ("lon_0".to_string(), ProjValue::Number(-97.0)),
            ("R".to_string(), ProjValue::Number(6_370_000.0)),
        ])
    }

    /// NEI2016 cone params, matching the Python `_NEI` parameterization.
    fn nei_params() -> HashMap<String, ProjValue> {
        HashMap::from([
            ("lat_1".to_string(), ProjValue::Number(33.0)),
            ("lat_2".to_string(), ProjValue::Number(45.0)),
            ("lat_0".to_string(), ProjValue::Number(40.0)),
            ("lon_0".to_string(), ProjValue::Number(-97.0)),
            ("R".to_string(), ProjValue::Number(6_370_997.0)),
        ])
    }

    #[test]
    fn parse_proj_string_campfire() {
        let p = parse_proj_string(CAMPFIRE_SR);
        assert_eq!(proj_text(&p, "proj"), Some("lcc"));
        assert_eq!(proj_number(&p, "lat_1"), Some(30.0));
        assert_eq!(proj_number(&p, "lat_2"), Some(60.0));
        assert_eq!(proj_number(&p, "lat_0"), Some(39.0));
        assert_eq!(proj_number(&p, "lon_0"), Some(-97.0));
        assert_eq!(proj_text(&p, "datum"), Some("WGS84"));
        assert_eq!(p.get("no_defs"), Some(&ProjValue::Flag));
        // +x_0=0 parses as a number, not a flag.
        assert_eq!(proj_number(&p, "x_0"), Some(0.0));
    }

    /// The 20-corner `lambert_conformal_construction` golden (Python
    /// `_CONSTRUCT_WRF`): `(x, y, lon, lat)`, inverse checked to `abs = 1e-9`.
    #[rustfmt::skip]
    const CONSTRUCT_WRF: [(f64, f64, f64, f64); 20] = [
        (-2e6, -1.5e6, -116.10017801101773, 23.320805943967475),
        (-1e6, -1.5e6, -106.68789739792601, 24.883956953152033),
        ( 0.0, -1.5e6,  -97.0,              25.415772540363083),
        ( 1e6, -1.5e6,  -87.31210260207399, 24.883956953152033),
        ( 2e6, -1.5e6,  -77.89982198898227, 23.320805943967475),
        (-2e6, -0.5e6, -118.62443079701725, 31.92388539661814),
        (-1e6, -0.5e6, -108.01300959338514, 33.76904204570805),
        ( 0.0, -0.5e6,  -97.0,              34.39829502737979),
        ( 1e6, -0.5e6,  -85.98699040661486, 33.76904204570805),
        ( 2e6, -0.5e6,  -75.37556920298275, 31.92388539661814),
        (-2e6,  0.5e6, -121.89275561686046, 40.7292258345734),
        (-1e6,  0.5e6, -109.75450863032499, 42.90012555470361),
        ( 0.0,  0.5e6,  -97.0,              43.64290686620447),
        ( 1e6,  0.5e6,  -84.24549136967501, 42.90012555470361),
        ( 2e6,  0.5e6,  -72.10724438313954, 40.7292258345734),
        (-2e6,  1.5e6, -126.27323349556194, 49.51039356753986),
        (-1e6,  1.5e6, -112.14243848502849, 52.06011386781491),
        ( 0.0,  1.5e6,  -97.0,              52.93698916474947),
        ( 1e6,  1.5e6,  -81.85756151497151, 52.06011386781491),
        ( 2e6,  1.5e6,  -67.72676650443806, 49.51039356753986),
    ];

    #[test]
    fn lcc_inverse_matches_esd_construction_golden() {
        let params = wrf_params();
        for (x, y, glon, glat) in CONSTRUCT_WRF {
            let (lon, lat) = lcc_inverse(x, y, &params).unwrap();
            assert!(
                (lon - glon).abs() < 1e-9,
                "lon at ({x},{y}): {lon} vs {glon}"
            );
            assert!(
                (lat - glat).abs() < 1e-9,
                "lat at ({x},{y}): {lat} vs {glat}"
            );
        }
    }

    /// LCC forward golden (Python `_REPROJ_COORDS` → `_REPROJ_FWD`), checked to
    /// `rel = 1e-7, abs = 1e-4`.
    #[rustfmt::skip]
    const REPROJ_COORDS: [(f64, f64); 8] = [
        (-97.0, 39.0), (-120.0, 35.0), (-75.0, 40.0), (-90.0, 45.0),
        (-100.0, 25.0), (-80.0, 48.0), (-110.0, 31.0), (-104.0, 42.5),
    ];

    #[rustfmt::skip]
    const REPROJ_FWD_WRF: [(f64, f64); 8] = [
        (0.0, 0.43226828519254923),
        (-2028208.5469169607, -140947.28851322923),
        (1795192.9893785124, 356152.97854254674),
        (530758.079019565, 668954.7596800169),
        (-309853.2783964032, -1541532.7554675443),
        (1213070.0930733175, 1097145.5185974697),
        (-1228247.943920761, -773888.551179463),
        (-554207.2432213802, 401411.8990695188),
    ];

    #[rustfmt::skip]
    const REPROJ_FWD_NEI: [(f64, f64); 8] = [
        (0.0, -110589.55965320487),
        (-2066463.053651542, -290403.0815928243),
        (1845776.3535729724, 224515.92418459523),
        (549842.4483977046, 575299.4792623082),
        (-309377.09304183396, -1668877.3176074345),
        (1266623.2685378056, 1007635.9929630421),
        (-1239963.1270495383, -909332.8255445026),
        (-571190.8151147817, 298694.874228091),
    ];

    fn approx_rel_abs(got: f64, want: f64, rel: f64, abs: f64) -> bool {
        (got - want).abs() <= abs + rel * want.abs()
    }

    #[test]
    fn lcc_forward_matches_esd_reproject_golden() {
        for (params, golden) in [
            (wrf_params(), REPROJ_FWD_WRF),
            (nei_params(), REPROJ_FWD_NEI),
        ] {
            for ((lon, lat), (gx, gy)) in REPROJ_COORDS.iter().zip(golden.iter()) {
                let (x, y) = lcc_forward(*lon, *lat, &params).unwrap();
                assert!(approx_rel_abs(x, *gx, 1e-7, 1e-4), "x: {x} vs {gx}");
                assert!(approx_rel_abs(y, *gy, 1e-7, 1e-4), "y: {y} vs {gy}");
            }
        }
    }

    #[test]
    fn lcc_roundtrip_identity() {
        let xs = [-2e6, -1e6, 0.0, 1e6, 2e6];
        let ys = [-1.5e6, 0.0, 1.5e6, 0.5e6, -0.5e6];
        for params in [wrf_params(), nei_params()] {
            let cone = lcc_cone(&params).unwrap();
            for (&x, &y) in xs.iter().zip(ys.iter()) {
                let (lon, lat) = lcc_inverse_cone(x, y, &cone);
                let (x2, y2) = lcc_forward_cone(lon, lat, &cone);
                assert!((x2 - x).abs() < 1e-6, "x roundtrip {x2} vs {x}");
                assert!((y2 - y).abs() < 1e-6, "y roundtrip {y2} vs {y}");
            }
        }
    }

    #[test]
    fn central_meridian_invariant() {
        // A point on the central meridian (x = 0) inverts to exactly lon_0.
        for params in [wrf_params(), nei_params()] {
            let (lon, _lat) = lcc_inverse(0.0, 0.5e6, &params).unwrap();
            assert!((lon - (-97.0)).abs() < 1e-12, "central meridian lon {lon}");
        }
    }

    #[test]
    fn longlat_reproject_is_identity() {
        for sr in [Some("+proj=longlat +datum=WGS84"), None, Some("")] {
            for (x, y) in [(-97.0, 39.0), (10.0, -20.0), (0.0, 0.0)] {
                let (lon, lat) = reproject_xy_to_lonlat(x, y, sr).unwrap();
                assert_eq!((lon, lat), (x, y), "identity for {sr:?}");
            }
        }
    }

    #[test]
    fn unsupported_projection_errors() {
        let err = Reprojector::from_spatial_ref(Some("+proj=merc +datum=WGS84")).unwrap_err();
        assert!(err.message().contains("merc"), "{}", err.message());
    }

    #[test]
    fn missing_standard_parallel_errors() {
        let params = HashMap::from([("lon_0".to_string(), ProjValue::Number(-97.0))]);
        assert!(lcc_cone(&params).is_err());
    }
}
