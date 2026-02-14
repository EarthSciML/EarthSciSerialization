"""Additional test scenarios for comprehensive _var placeholder expansion coverage."""

import json
import pytest
from esm_format import load
from esm_format.parse import _parse_expression
from esm_format.types import ExprNode, EsmFile


class TestPlaceholderScenarios:
    """Extended test scenarios for _var placeholder expansion."""

    def test_placeholder_in_atmospheric_chemistry(self):
        """Test _var placeholders in atmospheric chemistry contexts."""
        # Photolysis with _var
        photolysis_esm = {
            "esm": "0.1.0",
            "metadata": {"name": "Photolysis Test"},
            "models": {
                "Photolysis": {
                    "variables": {
                        "j_rate": {"type": "parameter", "units": "1/s", "default": 0.001}
                    },
                    "equations": [
                        {
                            "lhs": {"op": "D", "args": ["_var"], "wrt": "t"},
                            "rhs": {
                                "op": "*",
                                "args": [
                                    {"op": "-", "args": ["j_rate"]},
                                    "_var"
                                ]
                            }
                        }
                    ]
                }
            }
        }

        json_str = json.dumps(photolysis_esm)
        esm_file = load(json_str)

        model = esm_file.models[0]
        equation = model.equations[0]

        # Check photolysis loss term: -j_rate * _var
        rhs = equation.rhs
        assert rhs.op == "*"
        assert rhs.args[1] == "_var"

    def test_placeholder_in_oceanic_processes(self):
        """Test _var in oceanic mixing and transport models."""
        ocean_mixing = {
            "esm": "0.1.0",
            "metadata": {"name": "Ocean Mixing"},
            "models": {
                "VerticalMixing": {
                    "variables": {
                        "K_v": {"type": "parameter", "units": "m^2/s", "default": 1e-3},
                        "dz": {"type": "parameter", "units": "m", "default": 10.0}
                    },
                    "equations": [
                        {
                            "lhs": {"op": "D", "args": ["_var"], "wrt": "t"},
                            "rhs": {
                                "op": "*",
                                "args": [
                                    "K_v",
                                    {
                                        "op": "D",
                                        "args": [
                                            {"op": "D", "args": ["_var"], "wrt": "z"}
                                        ],
                                        "wrt": "z"
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
        }

        json_str = json.dumps(ocean_mixing)
        esm_file = load(json_str)

        equation = esm_file.models[0].equations[0]

        # Check second derivative term with _var (d/dz(d/dz(_var)))
        k_v_coeff = equation.rhs.args[0]
        second_deriv = equation.rhs.args[1]
        assert second_deriv.op == "D"
        assert second_deriv.wrt == "z"

        # Inner derivative should also contain _var
        inner_deriv = second_deriv.args[0]
        assert inner_deriv.op == "D"
        assert inner_deriv.args == ["_var"]
        assert inner_deriv.wrt == "z"

    def test_placeholder_in_biogeochemical_cycles(self):
        """Test _var in biogeochemical process models."""
        bgc_model = {
            "esm": "0.1.0",
            "metadata": {"name": "BGC Processes"},
            "models": {
                "Uptake": {
                    "variables": {
                        "V_max": {"type": "parameter", "units": "mol/m^3/s", "default": 0.1},
                        "K_m": {"type": "parameter", "units": "mol/m^3", "default": 1.0},
                        "biomass": {"type": "parameter", "units": "mol/m^3", "default": 10.0}
                    },
                    "equations": [
                        {
                            "lhs": {"op": "D", "args": ["_var"], "wrt": "t"},
                            "rhs": {
                                "op": "*",
                                "args": [
                                    {
                                        "op": "/",
                                        "args": [
                                            {
                                                "op": "*",
                                                "args": ["V_max", "_var"]
                                            },
                                            {
                                                "op": "+",
                                                "args": ["K_m", "_var"]
                                            }
                                        ]
                                    },
                                    "biomass"
                                ]
                            }
                        }
                    ]
                }
            }
        }

        json_str = json.dumps(bgc_model)
        esm_file = load(json_str)

        equation = esm_file.models[0].equations[0]

        # Check Michaelis-Menten kinetics with _var
        michaelis_term = equation.rhs.args[0]
        numerator = michaelis_term.args[0]
        denominator = michaelis_term.args[1]

        assert numerator.args[1] == "_var"  # V_max * _var
        assert denominator.args[1] == "_var"  # K_m + _var

    def test_placeholder_in_land_surface_processes(self):
        """Test _var in land surface and soil process models."""
        soil_model = {
            "esm": "0.1.0",
            "metadata": {"name": "Soil Processes"},
            "models": {
                "SoilDiffusion": {
                    "variables": {
                        "D_soil": {"type": "parameter", "units": "m^2/s", "default": 1e-6},
                        "porosity": {"type": "parameter", "units": "1", "default": 0.4},
                        "tortuosity": {"type": "parameter", "units": "1", "default": 0.67}
                    },
                    "equations": [
                        {
                            "lhs": {"op": "D", "args": ["_var"], "wrt": "t"},
                            "rhs": {
                                "op": "*",
                                "args": [
                                    {
                                        "op": "*",
                                        "args": [
                                            {
                                                "op": "*",
                                                "args": ["D_soil", "porosity"]
                                            },
                                            "tortuosity"
                                        ]
                                    },
                                    {"op": "laplacian", "args": ["_var"]}
                                ]
                            }
                        }
                    ]
                }
            }
        }

        json_str = json.dumps(soil_model)
        esm_file = load(json_str)

        equation = esm_file.models[0].equations[0]

        # Check soil diffusion with _var
        laplacian_term = equation.rhs.args[1]
        assert laplacian_term.op == "laplacian"
        assert laplacian_term.args == ["_var"]

    def test_placeholder_with_temperature_dependence(self):
        """Test _var in temperature-dependent processes."""
        temp_model = {
            "esm": "0.1.0",
            "metadata": {"name": "Temperature Dependent"},
            "models": {
                "Arrhenius": {
                    "variables": {
                        "A": {"type": "parameter", "units": "1/s", "default": 1e10},
                        "Ea": {"type": "parameter", "units": "J/mol", "default": 50000},
                        "R": {"type": "parameter", "units": "J/mol/K", "default": 8.314},
                        "T": {"type": "parameter", "units": "K", "default": 298.15}
                    },
                    "equations": [
                        {
                            "lhs": {"op": "D", "args": ["_var"], "wrt": "t"},
                            "rhs": {
                                "op": "*",
                                "args": [
                                    {
                                        "op": "*",
                                        "args": [
                                            "A",
                                            {
                                                "op": "exp",
                                                "args": [
                                                    {
                                                        "op": "/",
                                                        "args": [
                                                            {"op": "-", "args": ["Ea"]},
                                                            {"op": "*", "args": ["R", "T"]}
                                                        ]
                                                    }
                                                ]
                                            }
                                        ]
                                    },
                                    "_var"
                                ]
                            }
                        }
                    ]
                }
            }
        }

        json_str = json.dumps(temp_model)
        esm_file = load(json_str)

        equation = esm_file.models[0].equations[0]

        # Check Arrhenius rate multiplied by _var
        assert equation.rhs.args[1] == "_var"

    def test_placeholder_in_event_conditions(self):
        """Test _var in event-driven processes."""
        event_model = {
            "esm": "0.1.0",
            "metadata": {"name": "Event Model"},
            "models": {
                "EventDriven": {
                    "variables": {
                        "threshold": {"type": "parameter", "units": "mol/m^3", "default": 1.0}
                    },
                    "events": [
                        {
                            "name": "threshold_event",
                            "conditions": [
                                {"op": "-", "args": ["_var", "threshold"]}
                            ],
                            "affects": [
                                {
                                    "lhs": "_var",
                                    "rhs": {"op": "*", "args": [0.5, "_var"]}
                                }
                            ]
                        }
                    ]
                }
            }
        }

        # Note: This tests parsing of _var in event contexts
        # The current parser might not fully support events yet,
        # but the expression parsing should work
        condition_expr = {"op": "-", "args": ["_var", "threshold"]}
        affect_expr = {"op": "*", "args": [0.5, "_var"]}

        parsed_condition = _parse_expression(condition_expr)
        parsed_affect = _parse_expression(affect_expr)

        assert parsed_condition.args[0] == "_var"
        assert parsed_affect.args[1] == "_var"

    def test_placeholder_with_boundary_conditions(self):
        """Test _var in boundary condition specifications."""
        # Zero-flux boundary condition: grad(_var) · n = 0
        boundary_expr = {
            "op": "dot",
            "args": [
                {"op": "grad", "args": ["_var"]},
                "normal_vector"
            ]
        }

        expr = _parse_expression(boundary_expr)
        grad_term = expr.args[0]
        assert grad_term.args == ["_var"]

        # Dirichlet boundary: _var = fixed_value
        dirichlet_expr = {"op": "=", "args": ["_var", "boundary_value"]}
        expr = _parse_expression(dirichlet_expr)
        assert expr.args[0] == "_var"

        # Robin boundary: alpha * _var + beta * grad(_var) = gamma
        robin_expr = {
            "op": "=",
            "args": [
                {
                    "op": "+",
                    "args": [
                        {"op": "*", "args": ["alpha", "_var"]},
                        {"op": "*", "args": ["beta", {"op": "grad", "args": ["_var"]}]}
                    ]
                },
                "gamma"
            ]
        }

        expr = _parse_expression(robin_expr)
        left_side = expr.args[0]
        term1 = left_side.args[0]
        term2 = left_side.args[1]

        assert term1.args[1] == "_var"
        assert term2.args[1].args == ["_var"]

    def test_placeholder_in_coordinate_transformations(self):
        """Test _var with coordinate system transformations."""
        # Spherical coordinates transformation
        spherical_expr = {
            "op": "+",
            "args": [
                # radial term
                {
                    "op": "*",
                    "args": [
                        {"op": "/", "args": [1, {"op": "^", "args": ["r", 2]}]},
                        {
                            "op": "D",
                            "args": [
                                {
                                    "op": "*",
                                    "args": [
                                        {"op": "^", "args": ["r", 2]},
                                        {"op": "D", "args": ["_var"], "wrt": "r"}
                                    ]
                                }
                            ],
                            "wrt": "r"
                        }
                    ]
                },
                # angular terms would follow...
            ]
        }

        expr = _parse_expression(spherical_expr)

        # Navigate to find _var in the radial term
        radial_term = expr.args[0]
        inner_derivative = radial_term.args[1]
        multiplication = inner_derivative.args[0]
        variable_derivative = multiplication.args[1]

        assert variable_derivative.args == ["_var"]

    def test_placeholder_error_scenarios(self):
        """Test edge cases and potential error scenarios with _var."""
        # These should all parse successfully but represent edge cases

        # Division by _var (potential division by zero)
        div_expr = {"op": "/", "args": ["constant", "_var"]}
        expr = _parse_expression(div_expr)
        assert expr.args[1] == "_var"

        # Logarithm of _var (potential log of negative)
        log_expr = {"op": "log", "args": ["_var"]}
        expr = _parse_expression(log_expr)
        assert expr.args == ["_var"]

        # Square root of _var (potential sqrt of negative)
        sqrt_expr = {"op": "sqrt", "args": ["_var"]}
        expr = _parse_expression(sqrt_expr)
        assert expr.args == ["_var"]

        # Power with _var as base and exponent
        power_expr = {"op": "^", "args": ["_var", "_var"]}
        expr = _parse_expression(power_expr)
        assert expr.args == ["_var", "_var"]

    def test_placeholder_in_coupling_contexts(self):
        """Test _var in contexts relevant to system coupling."""
        # Model designed to be coupled via operator_compose
        coupling_model = {
            "esm": "0.1.0",
            "metadata": {"name": "Generic Operator"},
            "models": {
                "GenericProcess": {
                    "variables": {
                        "rate_constant": {"type": "parameter", "units": "1/s", "default": 0.01}
                    },
                    "equations": [
                        {
                            "_comment": "Generic first-order process applied to any state variable",
                            "lhs": {"op": "D", "args": ["_var"], "wrt": "t"},
                            "rhs": {
                                "op": "*",
                                "args": [
                                    {"op": "-", "args": ["rate_constant"]},
                                    "_var"
                                ]
                            }
                        }
                    ]
                }
            }
        }

        json_str = json.dumps(coupling_model)
        esm_file = load(json_str)

        equation = esm_file.models[0].equations[0]

        # This equation structure is typical for operator_compose coupling
        assert equation.lhs.args == ["_var"]
        assert equation.rhs.args[1] == "_var"

    def test_placeholder_mathematical_operations(self):
        """Test _var with various mathematical operations."""
        operations = [
            # Trigonometric
            {"op": "sin", "args": ["_var"]},
            {"op": "cos", "args": ["_var"]},
            {"op": "tan", "args": ["_var"]},

            # Hyperbolic
            {"op": "sinh", "args": ["_var"]},
            {"op": "cosh", "args": ["_var"]},
            {"op": "tanh", "args": ["_var"]},

            # Exponential and logarithmic
            {"op": "exp", "args": ["_var"]},
            {"op": "log", "args": ["_var"]},
            {"op": "log10", "args": ["_var"]},

            # Powers and roots
            {"op": "^", "args": ["_var", 2]},
            {"op": "sqrt", "args": ["_var"]},
            {"op": "abs", "args": ["_var"]},

            # Special functions
            {"op": "erf", "args": ["_var"]},
            {"op": "gamma", "args": ["_var"]},
        ]

        for op_data in operations:
            expr = _parse_expression(op_data)
            assert isinstance(expr, ExprNode)
            assert "_var" in expr.args

    def test_placeholder_multi_dimensional_operators(self):
        """Test _var with multi-dimensional differential operators."""
        # Vector calculus operations
        operators = [
            {"op": "grad", "args": ["_var"]},
            {"op": "div", "args": ["_var"]},
            {"op": "curl", "args": ["_var"]},
            {"op": "laplacian", "args": ["_var"]},
        ]

        for op_data in operators:
            expr = _parse_expression(op_data)
            assert expr.args == ["_var"]

        # Directional derivatives
        directional = {
            "op": "D",
            "args": ["_var"],
            "wrt": "x"
        }
        expr = _parse_expression(directional)
        assert expr.args == ["_var"]
        assert expr.wrt == "x"

    def test_placeholder_conservation_laws(self):
        """Test _var in conservation law formulations."""
        # Mass conservation: d(_var)/dt + div(flux) = source
        conservation_expr = {
            "op": "+",
            "args": [
                {"op": "D", "args": ["_var"], "wrt": "t"},
                {
                    "op": "div",
                    "args": [
                        {"op": "*", "args": ["velocity", "_var"]}
                    ]
                }
            ]
        }

        expr = _parse_expression(conservation_expr)
        time_deriv = expr.args[0]
        divergence = expr.args[1]

        assert time_deriv.args == ["_var"]
        assert divergence.args[0].args[1] == "_var"