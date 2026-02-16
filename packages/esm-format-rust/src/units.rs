//! Unit parsing and dimensional analysis

use std::collections::HashMap;
use std::fmt;

/// Represents a physical unit with dimensions
#[derive(Debug, Clone, PartialEq)]
pub struct Unit {
    /// Base dimensions with their powers
    dimensions: HashMap<Dimension, i32>,
    /// Scale factor for unit conversions
    scale: f64,
}

/// Base physical dimensions
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum Dimension {
    Mass,        // M
    Length,      // L
    Time,        // T
    Current,     // I (electric current)
    Temperature, // Θ (thermodynamic temperature)
    Amount,      // N (amount of substance)
    Luminosity,  // J (luminous intensity)
}

/// Error types for unit operations
#[derive(Debug, Clone, PartialEq)]
pub enum UnitError {
    ParseError(String),
    DimensionMismatch(String),
    UnknownUnit(String),
}

impl fmt::Display for UnitError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            UnitError::ParseError(msg) => write!(f, "Parse error: {}", msg),
            UnitError::DimensionMismatch(msg) => write!(f, "Dimension mismatch: {}", msg),
            UnitError::UnknownUnit(unit) => write!(f, "Unknown unit: {}", unit),
        }
    }
}

impl std::error::Error for UnitError {}

impl Unit {
    /// Create a dimensionless unit
    pub fn dimensionless() -> Self {
        Unit {
            dimensions: HashMap::new(),
            scale: 1.0,
        }
    }

    /// Create a unit with a single dimension
    pub fn base(dimension: Dimension, power: i32, scale: f64) -> Self {
        let mut dimensions = HashMap::new();
        if power != 0 {
            dimensions.insert(dimension, power);
        }
        Unit { dimensions, scale }
    }

    /// Check if two units have compatible dimensions
    pub fn is_compatible(&self, other: &Unit) -> bool {
        self.dimensions == other.dimensions
    }

    /// Multiply two units
    pub fn multiply(&self, other: &Unit) -> Unit {
        let mut dimensions = self.dimensions.clone();

        for (dim, power) in &other.dimensions {
            *dimensions.entry(dim.clone()).or_insert(0) += power;
            // Remove dimensions with zero power
            if dimensions[dim] == 0 {
                dimensions.remove(dim);
            }
        }

        Unit {
            dimensions,
            scale: self.scale * other.scale,
        }
    }

    /// Divide two units
    pub fn divide(&self, other: &Unit) -> Unit {
        let mut dimensions = self.dimensions.clone();

        for (dim, power) in &other.dimensions {
            *dimensions.entry(dim.clone()).or_insert(0) -= power;
            // Remove dimensions with zero power
            if dimensions[dim] == 0 {
                dimensions.remove(dim);
            }
        }

        Unit {
            dimensions,
            scale: self.scale / other.scale,
        }
    }

    /// Raise unit to a power
    pub fn power(&self, exponent: i32) -> Unit {
        let dimensions = self.dimensions
            .iter()
            .map(|(dim, power)| (dim.clone(), power * exponent))
            .filter(|(_, power)| *power != 0)
            .collect();

        Unit {
            dimensions,
            scale: self.scale.powi(exponent),
        }
    }
}

/// Parse a unit string into a Unit struct
///
/// Supports common unit notations like:
/// - "m/s" (meters per second)
/// - "kg*m/s^2" (kilogram meters per second squared)
/// - "mol/L" (moles per liter)
/// - "1" or "" (dimensionless)
///
/// # Arguments
///
/// * `unit_str` - String representation of the unit
///
/// # Returns
///
/// * `Result<Unit, UnitError>` - Parsed unit or error
pub fn parse_unit(unit_str: &str) -> Result<Unit, UnitError> {
    if unit_str.is_empty() || unit_str == "1" {
        return Ok(Unit::dimensionless());
    }

    // Get base unit definitions
    let base_units = get_base_units();

    // Simple parsing for basic cases
    if let Some(unit) = base_units.get(unit_str) {
        return Ok(unit.clone());
    }

    // Handle compound units with basic parsing
    if unit_str.contains("/") {
        let parts: Vec<&str> = unit_str.split('/').collect();
        if parts.len() == 2 {
            let numerator = parse_unit(parts[0])?;
            let denominator = parse_unit(parts[1])?;
            return Ok(numerator.divide(&denominator));
        }
    }

    if unit_str.contains("*") {
        let parts: Vec<&str> = unit_str.split('*').collect();
        if parts.len() == 2 {
            let left = parse_unit(parts[0])?;
            let right = parse_unit(parts[1])?;
            return Ok(left.multiply(&right));
        }
    }

    // Handle powers (simplified)
    if unit_str.contains("^") {
        let parts: Vec<&str> = unit_str.split('^').collect();
        if parts.len() == 2 {
            let base_unit = parse_unit(parts[0])?;
            let power: i32 = parts[1].parse()
                .map_err(|_| UnitError::ParseError(format!("Invalid power: {}", parts[1])))?;
            return Ok(base_unit.power(power));
        }
    }

    Err(UnitError::UnknownUnit(unit_str.to_string()))
}

/// Get commonly used base units
fn get_base_units() -> HashMap<String, Unit> {
    let mut units = HashMap::new();

    // Length units
    units.insert("m".to_string(), Unit::base(Dimension::Length, 1, 1.0));
    units.insert("cm".to_string(), Unit::base(Dimension::Length, 1, 0.01));
    units.insert("km".to_string(), Unit::base(Dimension::Length, 1, 1000.0));

    // Time units
    units.insert("s".to_string(), Unit::base(Dimension::Time, 1, 1.0));
    units.insert("min".to_string(), Unit::base(Dimension::Time, 1, 60.0));
    units.insert("h".to_string(), Unit::base(Dimension::Time, 1, 3600.0));
    units.insert("day".to_string(), Unit::base(Dimension::Time, 1, 86400.0));

    // Mass units
    units.insert("kg".to_string(), Unit::base(Dimension::Mass, 1, 1.0));
    units.insert("g".to_string(), Unit::base(Dimension::Mass, 1, 0.001));

    // Amount units
    units.insert("mol".to_string(), Unit::base(Dimension::Amount, 1, 1.0));

    // Temperature units
    units.insert("K".to_string(), Unit::base(Dimension::Temperature, 1, 1.0));

    // Derived units
    // Velocity: m/s
    units.insert("m/s".to_string(),
        Unit::base(Dimension::Length, 1, 1.0).divide(&Unit::base(Dimension::Time, 1, 1.0)));

    // Concentration: mol/L (mol/m^3)
    let liter = Unit::base(Dimension::Length, 3, 0.001); // 1 L = 0.001 m^3
    units.insert("mol/L".to_string(),
        Unit::base(Dimension::Amount, 1, 1.0).divide(&liter));
    units.insert("M".to_string(),
        Unit::base(Dimension::Amount, 1, 1.0).divide(&liter)); // Molarity

    // Force: kg*m/s^2 (Newton)
    units.insert("N".to_string(),
        Unit::base(Dimension::Mass, 1, 1.0)
            .multiply(&Unit::base(Dimension::Length, 1, 1.0))
            .divide(&Unit::base(Dimension::Time, 2, 1.0)));

    // Energy: kg*m^2/s^2 (Joule)
    units.insert("J".to_string(),
        Unit::base(Dimension::Mass, 1, 1.0)
            .multiply(&Unit::base(Dimension::Length, 2, 1.0))
            .divide(&Unit::base(Dimension::Time, 2, 1.0)));

    // Power: kg*m^2/s^3 (Watt)
    units.insert("W".to_string(),
        Unit::base(Dimension::Mass, 1, 1.0)
            .multiply(&Unit::base(Dimension::Length, 2, 1.0))
            .divide(&Unit::base(Dimension::Time, 3, 1.0)));

    units
}

/// Check dimensional consistency of an equation
///
/// # Arguments
///
/// * `lhs_unit` - Units of the left-hand side
/// * `rhs_unit` - Units of the right-hand side
///
/// # Returns
///
/// * `Result<(), UnitError>` - Ok if consistent, error otherwise
pub fn check_dimensional_consistency(lhs_unit: &Unit, rhs_unit: &Unit) -> Result<(), UnitError> {
    if lhs_unit.is_compatible(rhs_unit) {
        Ok(())
    } else {
        Err(UnitError::DimensionMismatch(
            "Left and right sides have incompatible dimensions".to_string()
        ))
    }
}

/// Convert between compatible units
///
/// # Arguments
///
/// * `value` - Value to convert
/// * `from_unit` - Source unit
/// * `to_unit` - Target unit
///
/// # Returns
///
/// * `Result<f64, UnitError>` - Converted value or error
pub fn convert_units(value: f64, from_unit: &Unit, to_unit: &Unit) -> Result<f64, UnitError> {
    if !from_unit.is_compatible(to_unit) {
        return Err(UnitError::DimensionMismatch(
            "Units have incompatible dimensions".to_string()
        ));
    }

    Ok(value * from_unit.scale / to_unit.scale)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_dimensionless() {
        let unit = parse_unit("").unwrap();
        assert_eq!(unit.dimensions.len(), 0);

        let unit = parse_unit("1").unwrap();
        assert_eq!(unit.dimensions.len(), 0);
    }

    #[test]
    fn test_parse_base_units() {
        let unit = parse_unit("m").unwrap();
        assert_eq!(unit.dimensions.get(&Dimension::Length), Some(&1));

        let unit = parse_unit("s").unwrap();
        assert_eq!(unit.dimensions.get(&Dimension::Time), Some(&1));

        let unit = parse_unit("kg").unwrap();
        assert_eq!(unit.dimensions.get(&Dimension::Mass), Some(&1));
    }

    #[test]
    fn test_parse_compound_units() {
        let unit = parse_unit("m/s").unwrap();
        assert_eq!(unit.dimensions.get(&Dimension::Length), Some(&1));
        assert_eq!(unit.dimensions.get(&Dimension::Time), Some(&-1));

        let unit = parse_unit("mol/L").unwrap();
        assert_eq!(unit.dimensions.get(&Dimension::Amount), Some(&1));
        assert_eq!(unit.dimensions.get(&Dimension::Length), Some(&-3));
    }

    #[test]
    fn test_unit_compatibility() {
        let m = parse_unit("m").unwrap();
        let cm = parse_unit("cm").unwrap();
        let s = parse_unit("s").unwrap();

        assert!(m.is_compatible(&cm));
        assert!(!m.is_compatible(&s));
    }

    #[test]
    fn test_unit_arithmetic() {
        let m = parse_unit("m").unwrap();
        let s = parse_unit("s").unwrap();

        let velocity = m.divide(&s);
        assert_eq!(velocity.dimensions.get(&Dimension::Length), Some(&1));
        assert_eq!(velocity.dimensions.get(&Dimension::Time), Some(&-1));

        let area = m.power(2);
        assert_eq!(area.dimensions.get(&Dimension::Length), Some(&2));
    }

    #[test]
    fn test_dimensional_consistency() {
        let m = parse_unit("m").unwrap();
        let cm = parse_unit("cm").unwrap();
        let s = parse_unit("s").unwrap();

        assert!(check_dimensional_consistency(&m, &cm).is_ok());
        assert!(check_dimensional_consistency(&m, &s).is_err());
    }

    #[test]
    fn test_unit_conversion() {
        let m = parse_unit("m").unwrap();
        let cm = parse_unit("cm").unwrap();

        let result = convert_units(1.0, &m, &cm).unwrap();
        assert!((result - 100.0).abs() < 1e-10);

        let result = convert_units(100.0, &cm, &m).unwrap();
        assert!((result - 1.0).abs() < 1e-10);
    }

    #[test]
    fn test_unknown_unit() {
        let result = parse_unit("unknown_unit");
        assert!(matches!(result, Err(UnitError::UnknownUnit(_))));
    }
}