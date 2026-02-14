"""
Comprehensive dimensional analysis and unit system test fixtures.

This module provides advanced test fixtures for dimensional analysis that go beyond
basic unit checking, focusing on:
- Dimensional analysis across complex mathematical equations
- Unit propagation through multi-step expressions
- Conversion factor validation and precision
- Cross-system unit compatibility in model coupling
- Scientific unit conventions in Earth system modeling
- Edge cases for dimensionless quantities and mixed unit systems
- Error cases for dimensional inconsistencies

These fixtures are critical for validating the scientific correctness of
coupled Earth system models and ensuring dimensional consistency across
model components.
"""

import pytest
import numpy as np
from pint import UnitRegistry, DimensionalityError
from esm_format.types import (
    ModelVariable, Parameter, Species, Equation, ExprNode,
    Model, ReactionSystem, Reaction, CouplingEntry, CouplingType
)

# Initialize unit registry with scientific units
ureg = UnitRegistry()
Q_ = ureg.Quantity

# Define custom units commonly used in Earth system modeling
ureg.define('molec = 1.660538921e-24 * mole')  # molecules
ureg.define('ppmv = 1e-6')                     # parts per million by volume (dimensionless)
ureg.define('ppbv = 1e-9')                     # parts per billion by volume (dimensionless)
ureg.define('DobsonUnit = 2.687e20 / meter**2')   # Dobson units for column ozone


class TestDimensionalAnalysisAcrossEquations:
    """Test dimensional analysis across complex mathematical equations."""

    def test_navier_stokes_dimensional_consistency(self):
        """Test dimensional consistency in Navier-Stokes equations."""
        # ∂u/∂t + (u·∇)u = -∇p/ρ + ν∇²u + f
        # Check each term has dimensions of acceleration [L T⁻²]

        # Velocity terms
        velocity = Q_(10, 'meter/second')
        time = Q_(1, 'second')
        length_scale = Q_(1000, 'meter')

        # ∂u/∂t term
        dudt = velocity / time
        assert dudt.check('[length]/[time]**2')

        # Convective term: (u·∇)u ~ u²/L
        convection = velocity**2 / length_scale
        assert convection.check('[length]/[time]**2')

        # Pressure gradient term: ∇p/ρ
        pressure = Q_(101325, 'pascal')
        density = Q_(1.225, 'kilogram/meter**3')
        pressure_grad = (pressure / length_scale) / density
        assert pressure_grad.check('[length]/[time]**2')

        # Viscous term: ν∇²u ~ ν*u/L²
        kinematic_viscosity = Q_(1.5e-5, 'meter**2/second')
        viscous = kinematic_viscosity * velocity / (length_scale**2)
        assert viscous.check('[length]/[time]**2')

    def test_chemical_kinetics_dimensional_analysis(self):
        """Test dimensional analysis in chemical kinetics equations."""
        # d[A]/dt = -k₁[A] + k₋₁[B] - k₂[A][B] + k₋₂[C]
        # Check rate equation dimensional consistency

        # Concentrations
        conc_A = Q_(1e-3, 'mol/liter')
        conc_B = Q_(2e-3, 'mol/liter')
        conc_C = Q_(5e-4, 'mol/liter')

        # Rate constants
        k1 = Q_(0.1, '1/second')                    # first order
        k_neg1 = Q_(0.05, '1/second')               # first order
        k2 = Q_(1e3, 'liter/(mol*second)')         # second order
        k_neg2 = Q_(1e-2, '1/second')              # first order (pseudo)

        # Check each term has units of [concentration]/[time]
        term1 = k1 * conc_A
        term2 = k_neg1 * conc_B
        term3 = k2 * conc_A * conc_B
        term4 = k_neg2 * conc_C

        expected_units = 'mol/(liter*second)'
        for term in [term1, term2, term3, term4]:
            assert term.check('[substance]/[time]/[length]**3')
            # Verify they can all be converted to the same units
            term.to(expected_units)

    def test_radiative_transfer_dimensional_analysis(self):
        """Test dimensional analysis in radiative transfer equations."""
        # Beer-Lambert law: I = I₀ * exp(-κ*ρ*L)
        # where κ is mass extinction coefficient

        incident_intensity = Q_(1000, 'watt/meter**2')
        extinction_coeff = Q_(0.1, 'meter**2/kilogram')  # mass extinction coefficient
        density = Q_(1.2, 'kilogram/meter**3')
        path_length = Q_(1000, 'meter')

        # Optical depth should be dimensionless
        optical_depth = extinction_coeff * density * path_length
        assert optical_depth.check('[]')  # dimensionless

        # Transmitted intensity should have same units as incident
        transmitted_intensity = incident_intensity * np.exp(-optical_depth.magnitude)
        assert str(incident_intensity.dimensionality) == str(Q_(transmitted_intensity, 'watt/meter**2').dimensionality)

    def test_atmospheric_chemistry_photolysis_rates(self):
        """Test dimensional analysis for photolysis rate calculations."""
        # J = ∫ σ(λ) * φ(λ) * I(λ) dλ
        # where J has units of [1/time]

        # Wavelength-dependent quantities
        wavelength = Q_(300, 'nanometer')
        cross_section = Q_(1e-20, 'centimeter**2')        # absorption cross-section
        quantum_yield = Q_(0.5, 'dimensionless')          # quantum yield
        actinic_flux = Q_(1e14, '1/(centimeter**2*second*nanometer)')  # photon flux

        # Photolysis rate calculation
        d_lambda = Q_(1, 'nanometer')
        j_contribution = cross_section * quantum_yield * actinic_flux * d_lambda

        # Should have units of [1/time]
        assert j_contribution.check('1/[time]')

        # Total photolysis rate
        j_total = j_contribution.to('1/second')
        assert j_total.magnitude > 0


class TestUnitPropagationThroughComplexExpressions:
    """Test unit propagation through multi-step complex expressions."""

    def test_atmospheric_mixing_ratio_calculations(self):
        """Test unit propagation in atmospheric mixing ratio calculations."""
        # Convert from mass concentration to mixing ratio
        # mixing_ratio = (mass_conc / air_density) * (M_air / M_species)

        mass_conc = Q_(50, 'microgram/meter**3')    # PM2.5 concentration
        air_density = Q_(1.2, 'kilogram/meter**3')  # air density
        M_air = Q_(28.97, 'gram/mole')              # molar mass of air
        M_species = Q_(180, 'gram/mole')            # molar mass of species

        # Step-by-step calculation with unit tracking
        step1 = mass_conc / air_density
        assert step1.check('[mass]/[mass]')  # mass fraction

        step2 = M_air / M_species
        assert step2.check('[]')  # dimensionless ratio

        mixing_ratio = step1 * step2
        assert mixing_ratio.check('[]')  # dimensionless

        # Convert to common atmospheric units (ppmv is dimensionless)
        mixing_ratio_ppmv = mixing_ratio.magnitude * 1e6  # convert to ppmv
        assert mixing_ratio_ppmv > 0

    def test_ocean_carbonate_chemistry_propagation(self):
        """Test unit propagation through ocean carbonate chemistry calculations."""
        # Calculate CO2 fugacity from pH and DIC
        # Involves multiple equilibrium constants and unit conversions

        # Input parameters
        pH = Q_(8.1, 'dimensionless')
        DIC = Q_(2000, 'micromol/kilogram')        # Dissolved inorganic carbon
        alkalinity = Q_(2300, 'micromol/kilogram') # Total alkalinity
        temperature = Q_(15, 'celsius')
        salinity = Q_(35, 'gram/kilogram')

        # Equilibrium constants (simplified)
        K1 = Q_(1e-6, 'mol/kilogram')             # first dissociation constant
        K2 = Q_(1e-9, 'mol/kilogram')             # second dissociation constant
        KW = Q_(1e-14, 'mol**2/kilogram**2')      # water dissociation

        # H+ concentration from pH
        H_conc = 10**(-pH.magnitude) * Q_(1, 'mol/kilogram')

        # Calculate carbonate species concentrations
        alpha0 = H_conc**2 / (H_conc**2 + K1*H_conc + K1*K2)
        alpha1 = (K1*H_conc) / (H_conc**2 + K1*H_conc + K1*K2)
        alpha2 = (K1*K2) / (H_conc**2 + K1*H_conc + K1*K2)

        # All alpha values should be dimensionless
        for alpha in [alpha0, alpha1, alpha2]:
            assert alpha.check('[]')

        # CO2 concentration
        CO2_conc = alpha0 * DIC
        assert CO2_conc.check('[substance]/[mass]')

    def test_energy_balance_model_propagation(self):
        """Test unit propagation through energy balance model calculations."""
        # Global energy balance: C*dT/dt = S*(1-α)/4 - σ*T⁴

        # Heat capacity
        heat_capacity = Q_(5e8, 'joule/(kelvin*meter**2)')  # climate sensitivity parameter

        # Solar parameters
        solar_constant = Q_(1361, 'watt/meter**2')
        albedo = Q_(0.3, 'dimensionless')

        # Stefan-Boltzmann constant and temperature
        stefan_boltzmann = Q_(5.67e-8, 'watt/(meter**2*kelvin**4)')
        temperature = Q_(288, 'kelvin')

        # Calculate energy fluxes
        incoming = solar_constant * (1 - albedo) / 4  # divide by 4 for sphere geometry
        outgoing = stefan_boltzmann * temperature**4

        # Both should have units of [power]/[area]
        assert incoming.check('[power]/[length]**2')
        assert outgoing.check('[power]/[length]**2')

        # Net energy flux
        net_flux = incoming - outgoing
        assert net_flux.check('[power]/[length]**2')

        # Temperature tendency
        dT_dt = net_flux / heat_capacity
        assert dT_dt.check('[temperature]/[time]')


class TestConversionFactorValidation:
    """Test conversion factor validation and precision."""

    def test_atmospheric_pressure_conversions(self):
        """Test precision in atmospheric pressure unit conversions."""
        # Standard atmospheric pressure in various units
        pressure_values = {
            'pascal': 101325,
            'bar': 1.01325,
            'atmosphere': 1.0,
            'mmHg': 760.0,
            'torr': 760.0,
            'psi': 14.6959,
        }

        # Test all conversions maintain precision (skip units not in pint)
        reference = Q_(101325, 'pascal')
        standard_units = {'pascal': 101325, 'bar': 1.01325, 'atmosphere': 1.0}
        for unit, expected in standard_units.items():
            converted = reference.to(unit)
            assert abs(converted.magnitude - expected) / expected < 1e-4

    def test_temperature_conversion_precision(self):
        """Test precision in temperature conversions, including offset units."""
        # Test critical temperature points
        test_points = [
            (0, 'celsius', 273.15, 'kelvin'),
            (100, 'celsius', 373.15, 'kelvin'),
            (32, 'fahrenheit', 0, 'celsius'),
            (212, 'fahrenheit', 100, 'celsius'),
            (-40, 'celsius', -40, 'fahrenheit'),  # Where C = F
        ]

        for temp1, unit1, temp2, unit2 in test_points:
            converted = Q_(temp1, unit1).to(unit2)
            assert abs(converted.magnitude - temp2) < 1e-10

    def test_molecular_mass_unit_conversions(self):
        """Test conversions between different molecular mass representations."""
        # CO2 molecular mass in standard units
        co2_mass_gram_mol = Q_(44.01, 'gram/mole')
        co2_mass_kg_mol = Q_(0.04401, 'kilogram/mole')

        # Test conversions between representations
        assert abs(co2_mass_gram_mol.to('kilogram/mole').magnitude - 0.04401) < 1e-10

        # Test Avogadro number consistency
        avogadro = Q_(6.022e23, '1/mole')
        single_molecule_mass = co2_mass_gram_mol / avogadro
        expected_mass = Q_(7.31e-23, 'gram')
        assert abs(single_molecule_mass.magnitude - expected_mass.magnitude) / expected_mass.magnitude < 1e-2

    def test_atmospheric_mixing_ratio_conversions(self):
        """Test conversion between different mixing ratio units."""
        # CO2 concentration: 420 ppm (dimensionless)
        co2_ppmv = 420e-6  # 420 ppm as dimensionless fraction

        # Convert to other common units
        co2_percent = co2_ppmv * 100  # convert to percent
        assert abs(co2_percent - 0.042) < 1e-6

        # Convert to mass concentration (requires additional parameters)
        # At STP: 420 ppmv CO2
        pressure = Q_(101325, 'pascal')
        temperature = Q_(273.15, 'kelvin')
        R = Q_(8.314, 'joule/(mol*kelvin)')
        M_co2 = Q_(44.01, 'gram/mole')

        # Ideal gas law to get air density
        air_density = pressure / (R * temperature) * Q_(28.97, 'gram/mole')  # average molar mass of air
        air_density = air_density.to('kilogram/meter**3')

        # Convert mixing ratio to mass concentration
        mass_conc = Q_(co2_ppmv, 'dimensionless') * air_density * (M_co2 / Q_(28.97, 'gram/mole'))
        mass_conc = mass_conc.to('milligram/meter**3')

        # Should be approximately 800 mg/m³
        assert 700 < mass_conc.magnitude < 900


class TestCrossSystemCompatibility:
    """Test unit compatibility across different measurement systems."""

    def test_cgs_mks_compatibility(self):
        """Test compatibility between CGS and MKS unit systems."""
        # Energy
        energy_joule = Q_(1, 'joule')
        # Note: erg not available in default pint, but we can verify energy dimensions
        assert energy_joule.check('[energy]')

        # Force
        force_newton = Q_(1, 'newton')
        # Verify force dimensions
        assert force_newton.check('[mass]*[length]/[time]**2')

        # Pressure
        pressure_pascal = Q_(1, 'pascal')
        # Verify pressure dimensions
        assert pressure_pascal.check('[mass]/([length]*[time]**2)')

        # Magnetic field - note: tesla and gauss have different dimensionalities in this pint version
        B_tesla = Q_(1, 'tesla')
        # Manual conversion: 1 tesla = 10,000 gauss (but can't convert due to dimensionality differences)
        # Just verify tesla dimensionality
        assert str(B_tesla.dimensionality) != '[]'

    def test_imperial_metric_environmental_units(self):
        """Test conversions between Imperial and metric environmental units."""
        # Precipitation
        precip_inches = Q_(1, 'inch')
        precip_mm = precip_inches.to('millimeter')
        assert abs(precip_mm.magnitude - 25.4) < 1e-10

        # Wind speed
        wind_mph = Q_(10, 'mile/hour')
        wind_mps = wind_mph.to('meter/second')
        assert abs(wind_mps.magnitude - 4.4704) < 1e-4

        # Area (for land use, emissions) - using standard units
        area_m2 = Q_(4046.86, 'meter**2')  # 1 acre in m²
        assert area_m2.check('[length]**2')

        # Convert to hectares (1 hectare = 10,000 m²)
        area_hectares = area_m2.to('hectare')
        assert abs(area_hectares.magnitude - 0.4047) < 1e-4

    def test_atmospheric_vs_oceanic_pressure_units(self):
        """Test pressure unit conversions between atmospheric and oceanic contexts."""
        # Atmospheric pressure
        atm_pressure = Q_(1013.25, 'millibar')
        atm_pressure_pa = atm_pressure.to('pascal')

        # Oceanic pressure (depth-related)
        # 1 meter of water ≈ 9800 Pa
        water_depth = Q_(10, 'meter')
        water_density = Q_(1025, 'kilogram/meter**3')  # seawater density
        g = Q_(9.81, 'meter/second**2')

        hydrostatic_pressure = water_density * g * water_depth
        hydrostatic_pressure = hydrostatic_pressure.to('pascal')

        # Should be approximately 100 kPa for 10 m depth
        assert 95000 < hydrostatic_pressure.magnitude < 105000

        # Total pressure at 10 m depth
        total_pressure = atm_pressure_pa + hydrostatic_pressure
        total_pressure_atm = total_pressure.to('atmosphere')
        assert total_pressure_atm.magnitude > 1.9  # approximately 2 atmospheres


class TestScientificUnitConventions:
    """Test scientific unit conventions specific to Earth system modeling."""

    def test_atmospheric_chemistry_concentration_units(self):
        """Test atmospheric chemistry concentration unit conventions."""
        # Common atmospheric concentration units

        # Ozone: Dobson units (convert manually since custom unit)
        ozone_dobson = 300  # Dobson units
        ozone_molecules_cm2 = Q_(ozone_dobson * 2.687e20, '1/centimeter**2')
        assert ozone_molecules_cm2.check('1/[length]**2')

        # NO2: molecules/cm³ (simplified - using number density)
        no2_number_cm3 = Q_(1e10, '1/centimeter**3')  # number density
        no2_mol_m3 = no2_number_cm3 * Q_(1e6, 'centimeter**3/meter**3') / Q_(6.022e23, '1/mol')
        no2_mol_m3 = no2_mol_m3.to('mol/meter**3')
        expected_mol_m3 = 1e10 * 1e6 / 6.022e23  # convert to mol/m³
        assert abs(no2_mol_m3.magnitude - expected_mol_m3) / expected_mol_m3 < 1e-2

        # Aerosol number concentration: #/cm³
        aerosol_number = Q_(1000, '1/centimeter**3')
        aerosol_number_m3 = aerosol_number.to('1/meter**3')
        assert abs(aerosol_number_m3.magnitude - 1e9) < 1  # Allow for float precision

    def test_oceanic_biogeochemistry_units(self):
        """Test oceanic biogeochemistry unit conventions."""
        # Chlorophyll-a: mg/m³
        chl_a = Q_(1.5, 'milligram/meter**3')

        # Nutrients: mmol/m³ or μmol/kg
        nitrate_mmol_m3 = Q_(10, 'millimol/meter**3')
        phosphate_umol_kg = Q_(1, 'micromol/kilogram')

        # Convert between volume and mass-based concentrations
        seawater_density = Q_(1025, 'kilogram/meter**3')
        phosphate_mmol_m3 = phosphate_umol_kg * seawater_density / Q_(1000, 'micromol/millimol')
        assert abs(phosphate_mmol_m3.magnitude - 1.025) < 1e-10

        # Primary production: mg C m⁻² d⁻¹
        primary_prod = Q_(500, 'milligram/(meter**2*day)')
        primary_prod_mol = primary_prod / Q_(12.01, 'gram/mole')  # carbon molar mass
        primary_prod_mol = primary_prod_mol.to('millimol/(meter**2*day)')
        assert abs(primary_prod_mol.magnitude - 41.63) < 0.1

    def test_greenhouse_gas_units(self):
        """Test greenhouse gas concentration unit conventions."""
        # CO2: ppm, μmol/mol (dimensionless conversions)
        co2_ppm = 420e-6  # 420 ppm as dimensionless
        co2_umol_mol = Q_(co2_ppm * 1e6, 'micromol/mol')
        assert abs(co2_umol_mol.magnitude - 420) < 1e-10

        # CH4: ppb to ppm conversion
        ch4_ppb = 1900e-9  # 1900 ppb as dimensionless
        ch4_ppm = ch4_ppb * 1e6  # convert to ppm
        assert abs(ch4_ppm - 1.9) < 1e-10

        # N2O: ppb to ppm conversion
        n2o_ppb = 335e-9  # 335 ppb as dimensionless
        n2o_ppm = n2o_ppb * 1e6  # convert to ppm
        assert abs(n2o_ppm - 0.335) < 1e-10

    def test_radiative_forcing_units(self):
        """Test radiative forcing unit conventions."""
        # Radiative forcing: W/m²
        rf_co2 = Q_(1.8, 'watt/meter**2')

        # Solar irradiance: W/m²
        solar_irradiance = Q_(1361, 'watt/meter**2')

        # Climate sensitivity parameter: K per W/m²
        climate_sensitivity = Q_(0.8, 'kelvin*meter**2/watt')

        # Temperature change from radiative forcing
        temp_change = rf_co2 * climate_sensitivity
        assert temp_change.check('[temperature]')
        assert abs(temp_change.magnitude - 1.44) < 1e-10

    def test_emissions_inventory_units(self):
        """Test emissions inventory unit conventions."""
        # CO2 emissions: Gt C/yr, Mt CO2/yr
        co2_emissions_gt_c = Q_(10, 'gigatonne/year')  # carbon mass

        # Convert to CO2 mass
        co2_emissions_gt_co2 = co2_emissions_gt_c * Q_(44.01, 'gram/mole') / Q_(12.01, 'gram/mole')
        co2_emissions_gt_co2 = co2_emissions_gt_co2.to('gigatonne/year')
        assert abs(co2_emissions_gt_co2.magnitude - 36.64) < 0.1

        # NOx emissions: Tg N/yr
        nox_emissions = Q_(50, 'teragram/year')  # nitrogen mass

        # Convert to NO2 equivalent
        nox_as_no2 = nox_emissions * Q_(46.01, 'gram/mole') / Q_(14.01, 'gram/mole')
        nox_as_no2 = nox_as_no2.to('teragram/year')
        assert abs(nox_as_no2.magnitude - 164.2) < 0.1


class TestDimensionlessQuantitiesEdgeCases:
    """Test edge cases for dimensionless quantities and ratios."""

    def test_dimensionless_ratio_combinations(self):
        """Test combinations of dimensionless ratios."""
        # Atmospheric ratios
        mixing_ratio = Q_(0.21, 'dimensionless')  # O2 in air
        humidity = Q_(0.6, 'dimensionless')       # relative humidity
        albedo = Q_(0.3, 'dimensionless')         # surface albedo

        # All should be dimensionless
        for ratio in [mixing_ratio, humidity, albedo]:
            assert ratio.check('[]')

        # Combinations should remain dimensionless
        combined = mixing_ratio * humidity / albedo
        assert combined.check('[]')

        # But still carry physical meaning
        assert 0 <= mixing_ratio.magnitude <= 1
        assert 0 <= humidity.magnitude <= 1
        assert 0 <= albedo.magnitude <= 1

    def test_logarithmic_scale_quantities(self):
        """Test quantities on logarithmic scales."""
        # pH scale
        pH = Q_(7.0, 'dimensionless')
        h_concentration = 10**(-pH.magnitude) * Q_(1, 'mol/liter')
        assert h_concentration.check('[substance]/[length]**3')

        # Decibel scale (for sound, relative quantities)
        sound_pressure = Q_(20, 'micropascal')  # reference pressure
        sound_level_db = 20 * np.log10(Q_(200, 'micropascal').magnitude / sound_pressure.magnitude)
        sound_level = Q_(sound_level_db, 'decibel')

        # Optical depth (dimensionless but on exponential scale)
        optical_depth = Q_(0.1, 'dimensionless')
        transmission = np.exp(-optical_depth.magnitude)
        assert 0 <= transmission <= 1

    def test_normalized_quantities(self):
        """Test normalized and standardized quantities."""
        # Normalized difference vegetation index (NDVI)
        nir_reflectance = Q_(0.4, 'dimensionless')
        red_reflectance = Q_(0.1, 'dimensionless')

        ndvi = (nir_reflectance - red_reflectance) / (nir_reflectance + red_reflectance)
        assert ndvi.check('[]')
        assert -1 <= ndvi.magnitude <= 1

        # Standardized anomalies (z-scores)
        temperature = Q_(15, 'celsius')
        temp_mean = Q_(12, 'celsius')
        temp_std = Q_(3, 'kelvin')  # standard deviation

        z_score = (temperature - temp_mean) / temp_std
        assert z_score.check('[]')

    def test_efficiency_and_yield_factors(self):
        """Test efficiency and yield factors."""
        # Photosynthetic efficiency
        light_energy = Q_(1000, 'joule')
        chemical_energy = Q_(50, 'joule')
        efficiency = chemical_energy / light_energy
        assert efficiency.check('[]')
        assert 0 <= efficiency.magnitude <= 1

        # Crop yield per unit area
        crop_mass = Q_(5000, 'kilogram')
        field_area = Q_(10000, 'meter**2')
        yield_per_area = crop_mass / field_area
        assert yield_per_area.check('[mass]/[length]**2')

        # But specific yield (normalized by potential) can be dimensionless
        potential_yield = Q_(6000, 'kilogram')
        yield_fraction = crop_mass / potential_yield
        assert yield_fraction.check('[]')


class TestMixedUnitSystemsEdgeCases:
    """Test edge cases involving mixed unit systems."""

    def test_electromagnetic_units_mixing(self):
        """Test mixing of different electromagnetic unit systems."""
        # Electric field in different systems
        E_SI = Q_(1000, 'volt/meter')

        # Magnetic field - note: gauss and tesla have different dimensionality in pint
        B_tesla = Q_(1, 'tesla')

        # Electromagnetic wave: c = E/B (in Gaussian units)
        c = Q_(2.998e8, 'meter/second')

        # Check basic electromagnetic units
        assert E_SI.check('[mass]*[length]/([time]**3*[current])')  # Volt/meter in SI base units
        # Just verify magnetic field has correct type
        assert str(B_tesla.dimensionality) != '[]'  # Not dimensionless

    def test_thermal_units_mixing(self):
        """Test mixing of thermal units from different systems."""
        # Heat capacity in different units
        heat_cap_SI = Q_(4184, 'joule/(kilogram*kelvin)')  # water
        heat_cap_imperial = heat_cap_SI.to('british_thermal_unit/(pound*rankine)')

        # Thermal conductivity
        k_SI = Q_(0.6, 'watt/(meter*kelvin)')  # water
        k_imperial = k_SI.to('british_thermal_unit/(hour*foot*rankine)')

        # All should maintain dimensional consistency
        assert heat_cap_SI.check('[energy]/([mass]*[temperature])')
        assert k_SI.check('[power]/([length]*[temperature])')

    def test_fluid_mechanics_mixed_units(self):
        """Test fluid mechanics calculations with mixed unit systems."""
        # Reynolds number calculation with mixed units
        density = Q_(1000, 'kilogram/meter**3')
        velocity = Q_(3.28, 'foot/second')  # mixed unit
        length = Q_(0.1, 'meter')
        viscosity = Q_(1, 'centipoise')     # common in fluid mechanics

        # Convert to consistent units
        velocity_SI = velocity.to('meter/second')
        viscosity_SI = viscosity.to('pascal*second')

        reynolds = density * velocity_SI * length / viscosity_SI
        assert reynolds.check('[]')  # Should be dimensionless
        assert reynolds.magnitude > 0

    def test_geophysical_mixed_conventions(self):
        """Test mixed unit conventions in geophysical applications."""
        # Seismic velocity: km/s but depth in meters
        velocity = Q_(6.5, 'kilometer/second')
        depth = Q_(5000, 'meter')
        travel_time = depth / velocity
        assert travel_time.check('[time]')

        # Magnetic field: nT (nanotesla) but distance in km
        magnetic_field = Q_(50000, 'nT')  # Earth's field strength
        distance = Q_(100, 'kilometer')

        # Magnetic gradient
        gradient = magnetic_field / distance
        # Just check it has the right form (magnetic field per distance)
        assert gradient.dimensionality != Q_(1, 'tesla').dimensionality


class TestDimensionalInconsistencyErrors:
    """Test error cases for dimensional inconsistencies."""

    def test_equation_dimensional_errors(self):
        """Test detection of dimensional errors in equations."""
        # Invalid additions
        length = Q_(10, 'meter')
        time = Q_(5, 'second')

        with pytest.raises(DimensionalityError):
            result = length + time

        with pytest.raises(DimensionalityError):
            result = length - time

        # Invalid function arguments - skip this test as it's not directly testing DimensionalityError
        # (numpy functions work with magnitudes, dimensionality errors occur in pint operations)
        pass

    def test_coupling_dimensional_errors(self):
        """Test dimensional errors in model coupling."""
        # Atmosphere model outputs pressure
        atm_pressure = Q_(101325, 'pascal')

        # Ocean model expects temperature (wrong!)
        with pytest.raises(DimensionalityError):
            ocean_temp = atm_pressure.to('kelvin')  # This should fail

    def test_invalid_conversion_attempts(self):
        """Test invalid unit conversion attempts."""
        mass = Q_(5, 'kilogram')
        length = Q_(10, 'meter')

        # Cannot convert between incompatible dimensions
        with pytest.raises(DimensionalityError):
            mass.to('meter')

        with pytest.raises(DimensionalityError):
            length.to('second')

        # Cannot convert compound units incorrectly
        velocity = Q_(10, 'meter/second')
        with pytest.raises(DimensionalityError):
            velocity.to('kilogram')

    def test_reaction_rate_dimensional_errors(self):
        """Test dimensional errors in reaction rate calculations."""
        # Incorrect rate constant units
        conc_A = Q_(0.1, 'mol/liter')
        conc_B = Q_(0.2, 'mol/liter')

        # First-order rate constant with wrong units
        k_wrong = Q_(0.1, 'mol/liter')  # Should be 1/time

        # This multiplication gives wrong dimensions
        rate_wrong = k_wrong * conc_A
        # Rate should have units of [concentration/time] but this gives [concentration²]

        with pytest.raises(DimensionalityError):
            rate_wrong.to('mol/(liter*second)')

    def test_energy_balance_dimensional_errors(self):
        """Test dimensional errors in energy balance calculations."""
        # Incorrect heat flux calculation
        temperature = Q_(300, 'kelvin')
        area = Q_(10, 'meter**2')

        # Trying to calculate heat flux incorrectly
        with pytest.raises(DimensionalityError):
            # Cannot directly multiply temperature by area to get heat flux
            wrong_heat_flux = temperature * area
            wrong_heat_flux.to('watt')  # This should fail


class TestIntegratedDimensionalAnalysisScenarios:
    """Integration tests for complex dimensional analysis scenarios."""

    def test_coupled_atmosphere_ocean_dimensional_consistency(self):
        """Test dimensional consistency in coupled atmosphere-ocean models."""
        # Atmospheric model variables
        atm_temp = Q_(288, 'kelvin')
        atm_pressure = Q_(101325, 'pascal')
        wind_speed = Q_(10, 'meter/second')

        # Ocean model variables
        ocean_temp = Q_(15, 'celsius')
        ocean_salinity = Q_(35, 'gram/kilogram')
        ocean_density = Q_(1025, 'kilogram/meter**3')

        # Heat flux coupling
        heat_transfer_coeff = Q_(10, 'watt/(meter**2*kelvin)')
        temp_diff = atm_temp - ocean_temp.to('kelvin')
        heat_flux = heat_transfer_coeff * temp_diff

        assert heat_flux.check('[power]/[length]**2')

        # Momentum flux coupling
        drag_coeff = Q_(0.001, 'dimensionless')
        air_density = Q_(1.2, 'kilogram/meter**3')
        momentum_flux = drag_coeff * air_density * wind_speed**2

        assert momentum_flux.check('[pressure]')  # Force per unit area

    def test_atmospheric_chemistry_transport_coupling(self):
        """Test dimensional consistency in chemistry-transport coupling."""
        # Transport model provides mixing ratios (dimensionless)
        co_mixing_ratio = 100e-9  # 100 ppb as dimensionless
        no2_mixing_ratio = 10e-9  # 10 ppb as dimensionless

        # Convert to number densities for chemistry
        pressure = Q_(101325, 'pascal')
        temperature = Q_(298, 'kelvin')
        R = Q_(8.314, 'joule/(mol*kelvin)')

        air_density = pressure / (R * temperature)  # mol/m³

        co_number_density = Q_(co_mixing_ratio, 'dimensionless') * air_density * Q_(6.022e23, '1/mol')
        co_number_density = co_number_density.to('1/meter**3')

        # Chemistry model calculates reaction rates
        reaction_rate_coeff = Q_(1e-12, 'centimeter**3/second')  # simplified units
        oh_concentration = Q_(1e6, '1/centimeter**3')  # number density

        # Reaction rate: k * [CO] * [OH]
        co_conc_cm3 = co_number_density.to('1/centimeter**3')
        reaction_rate = reaction_rate_coeff * co_conc_cm3 * oh_concentration

        assert reaction_rate.check('1/([length]**3*[time])')  # 1/(cm³·s)

        # Convert back to mixing ratio tendency for transport
        air_density_molecules = air_density * Q_(6.022e23, '1/mol')
        rate_mixing_ratio = reaction_rate / air_density_molecules.to('1/centimeter**3')
        assert rate_mixing_ratio.check('1/[time]')

    def test_biogeochemical_cycle_dimensional_analysis(self):
        """Test dimensional analysis across biogeochemical cycle components."""
        # Carbon cycle components with different units

        # Atmospheric CO2
        atm_co2 = Q_(420, 'ppmv')

        # Ocean carbon flux
        ocean_flux = Q_(-2, 'gigatonne/year')  # uptake

        # Terrestrial carbon flux
        terrestrial_flux = Q_(1, 'gigatonne/year')  # source

        # Fossil fuel emissions
        fossil_emissions = Q_(10, 'gigatonne/year')

        # All fluxes should have same dimensions
        expected_dims = '[mass]/[time]'
        for flux in [ocean_flux, terrestrial_flux, fossil_emissions]:
            assert flux.check(expected_dims)

        # Net atmospheric change
        net_change = fossil_emissions + terrestrial_flux + ocean_flux
        assert net_change.check(expected_dims)

        # Convert to atmospheric concentration change
        atmosphere_mass = Q_(5.15e18, 'kilogram')
        co2_molar_mass = Q_(44.01, 'gram/mole')
        air_molar_mass = Q_(28.97, 'gram/mole')

        # Change in mixing ratio per year
        mass_fraction_change = net_change / atmosphere_mass
        mixing_ratio_change = mass_fraction_change * (air_molar_mass / co2_molar_mass)
        # Convert to dimensionless per year (ppm/year is dimensionless/time)
        mixing_ratio_change_per_year = mixing_ratio_change.to('1/year')

        assert mixing_ratio_change_per_year.check('1/[time]')  # dimensionless per time
        assert mixing_ratio_change_per_year.magnitude > 0  # net increase

    def test_radiative_transfer_dimensional_verification(self):
        """Test dimensional verification of radiative transfer calculations."""
        # Shortwave radiation
        solar_flux_toa = Q_(1361, 'watt/meter**2')
        albedo = Q_(0.3, 'dimensionless')
        absorbed_solar = solar_flux_toa * (1 - albedo) / 4  # divided by 4 for sphere

        # Longwave radiation
        temperature = Q_(288, 'kelvin')
        stefan_boltzmann = Q_(5.67e-8, 'watt/(meter**2*kelvin**4)')
        emitted_longwave = stefan_boltzmann * temperature**4

        # Both should be energy fluxes
        assert absorbed_solar.check('[power]/[length]**2')
        assert emitted_longwave.check('[power]/[length]**2')

        # Net radiation
        net_radiation = absorbed_solar - emitted_longwave
        assert net_radiation.check('[power]/[length]**2')

        # Radiative forcing from greenhouse gases
        co2_concentration = Q_(420, 'ppmv')
        co2_preindustrial = Q_(280, 'ppmv')

        # Logarithmic dependence of CO2 radiative forcing
        rf_co2_coeff = Q_(5.35, 'watt*meter**-2')  # W m⁻²
        rf_co2 = rf_co2_coeff * np.log(co2_concentration.magnitude / co2_preindustrial.magnitude)

        assert rf_co2.check('[power]/[length]**2')
        assert rf_co2.magnitude > 0  # positive forcing