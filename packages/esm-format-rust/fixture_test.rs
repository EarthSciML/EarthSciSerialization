//! Test display functionality against fixtures
use std::fs;

fn main() {
    // Test chemical subscripts from fixture
    let chemical_tests = vec![
        ("O3", "O₃"),
        ("NO2", "NO₂"),
        ("CH2O", "CH₂O"),
        ("H2O2", "H₂O₂"),
        ("CO2", "CO₂"),
        ("NH3", "NH₃"),
        ("SO4", "SO₄"),
        ("Ca2", "Ca₂"),
        ("CH4", "CH₄"),
        ("C2H6", "C₂H₆"),
        ("C6H12O6", "C₆H₁₂O₆"),
        ("Fe2O3", "Fe₂O₃"),
        ("Al2O3", "Al₂O₃"),
    ];

    println!("Testing chemical subscript formatting:");
    for (input, expected) in chemical_tests {
        let result = format_chemical_subscripts(input);
        println!("{:<10} -> {:<10} (expected: {})", input, result, expected);
        assert_eq!(result, expected, "Failed for {}", input);
    }

    println!("\nAll chemical subscript tests passed!");
}

/// Convert a string with chemical subscripts to Unicode
fn format_chemical_subscripts(s: &str) -> String {
    const ELEMENTS: &[&str; 118] = &[
        "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
        "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca",
        "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn",
        "Ga", "Ge", "As", "Se", "Br", "Kr", "Rb", "Sr", "Y", "Zr",
        "Nb", "Mo", "Tc", "Ru", "Rh", "Pd", "Ag", "Cd", "In", "Sn",
        "Sb", "Te", "I", "Xe", "Cs", "Ba", "La", "Ce", "Pr", "Nd",
        "Pm", "Sm", "Eu", "Gd", "Tb", "Dy", "Ho", "Er", "Tm", "Yb",
        "Lu", "Hf", "Ta", "W", "Re", "Os", "Ir", "Pt", "Au", "Hg",
        "Tl", "Pb", "Bi", "Po", "At", "Rn", "Fr", "Ra", "Ac", "Th",
        "Pa", "U", "Np", "Pu", "Am", "Cm", "Bk", "Cf", "Es", "Fm",
        "Md", "No", "Lr", "Rf", "Db", "Sg", "Bh", "Hs", "Mt", "Ds",
        "Rg", "Cn", "Nh", "Fl", "Mc", "Lv", "Ts", "Og"
    ];

    const UNICODE_SUBSCRIPTS: [char; 10] = ['₀', '₁', '₂', '₃', '₄', '₅', '₆', '₇', '₈', '₉'];

    let mut result = String::new();
    let chars: Vec<char> = s.chars().collect();
    let mut i = 0;

    while i < chars.len() {
        let ch = chars[i];

        if ch.is_alphabetic() {
            // Try to match 2-letter element symbol first
            if i + 1 < chars.len() {
                let two_letter = format!("{}{}", ch, chars[i + 1]);
                if ELEMENTS.contains(&two_letter.as_str()) {
                    result.push_str(&two_letter);
                    i += 2;

                    // Convert following digits to subscripts
                    while i < chars.len() && chars[i].is_ascii_digit() {
                        let digit = chars[i].to_digit(10).unwrap();
                        result.push(UNICODE_SUBSCRIPTS[digit as usize]);
                        i += 1;
                    }
                    continue;
                }
            }

            // Try 1-letter element symbol
            if ELEMENTS.contains(&ch.to_string().as_str()) {
                result.push(ch);
                i += 1;

                // Convert following digits to subscripts
                while i < chars.len() && chars[i].is_ascii_digit() {
                    let digit = chars[i].to_digit(10).unwrap();
                    result.push(UNICODE_SUBSCRIPTS[digit as usize]);
                    i += 1;
                }
                continue;
            }

            // Not an element symbol, just add the character
            result.push(ch);
            i += 1;
        } else {
            result.push(ch);
            i += 1;
        }
    }

    result
}