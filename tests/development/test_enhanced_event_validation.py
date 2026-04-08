#!/usr/bin/env python3
"""
Test script to verify enhanced event validation functionality.
This tests the fixes for task EarthSciSerialization-rr42:
Python Event validation incomplete - no checks for affect variables, functional affect params, discrete_parameters
"""

import sys
sys.path.insert(0, 'packages/esm_format/src')

from esm_format.validation import validate
from esm_format.esm_types import (
    EsmFile, ContinuousEvent, DiscreteEvent, AffectEquation, FunctionalAffect,
    Metadata, Model, ModelVariable, Operator, Parameter, ReactionSystem, Species,
    CouplingEntry, CouplingType, DiscreteEventTrigger
)

def test_affect_neg_validation():
    """Test that affect_neg (direction-dependent affects) variables are validated."""
    print("=== Test 1: affect_neg validation ===")

    test_event = ContinuousEvent(
        name='test_event',
        conditions=[{'op': 'gt', 'args': ['t', 1.0]}],
        affects=[AffectEquation(lhs='x', rhs=2.0)],
        affect_neg=[
            AffectEquation(lhs='y', rhs=3.0),  # y exists - should pass
            AffectEquation(lhs='unknown_var', rhs=4.0)  # unknown_var doesn't exist - should fail
        ]
    )

    test_model = Model(
        name='test_model',
        variables={
            'x': ModelVariable(type='state'),
            'y': ModelVariable(type='state')
        },
        equations=[
            {'lhs': 'dx_dt', 'rhs': 1.0},
            {'lhs': 'dy_dt', 'rhs': 1.0}
        ]
    )

    test_file = EsmFile(
        version='1.0',
        metadata=Metadata(title='test affect_neg'),
        models={'test_model': test_model},
        events=[test_event]
    )

    result = validate(test_file)

    # Should have exactly 1 error for unknown_var
    affect_neg_errors = [e for e in result.structural_errors if 'affect_neg' in e.code]
    print(f"affect_neg validation errors: {len(affect_neg_errors)}")
    for error in affect_neg_errors:
        print(f"  {error.code}: {error.message}")

    assert len(affect_neg_errors) == 1
    assert 'unknown_var' in affect_neg_errors[0].message
    print("✓ affect_neg validation test passed\n")


def test_functional_affect_validation():
    """Test that FunctionalAffect parameters are validated."""
    print("=== Test 2: FunctionalAffect validation ===")

    test_event = ContinuousEvent(
        name='test_event',
        conditions=[{'op': 'gt', 'args': ['t', 1.0]}],
        affects=[
            FunctionalAffect(
                handler_id='valid_handler',  # This handler exists
                read_vars=['x', 'unknown_read_var'],  # x exists, unknown_read_var doesn't
                read_params=['p1', 'unknown_read_param'],  # p1 exists, unknown_read_param doesn't
                modified_params=['p2', 'unknown_mod_param']  # p2 exists, unknown_mod_param doesn't
            ),
            FunctionalAffect(
                handler_id='invalid_handler',  # This handler doesn't exist
                read_vars=['x'],
                read_params=['p1'],
                modified_params=['p2']
            )
        ]
    )

    test_model = Model(
        name='test_model',
        variables={
            'x': ModelVariable(type='state'),
            'p1': ModelVariable(type='parameter'),
            'p2': ModelVariable(type='parameter')
        },
        equations=[{'lhs': 'dx_dt', 'rhs': 1.0}]
    )

    test_operator = Operator(operator_id='valid_handler')

    test_file = EsmFile(
        version='1.0',
        metadata=Metadata(title='test functional affects'),
        models={'test_model': test_model},
        events=[test_event],
        operators=[test_operator]
    )

    result = validate(test_file)

    # Should have errors for: invalid_handler, unknown_read_var, unknown_read_param, unknown_mod_param
    functional_errors = [e for e in result.structural_errors if any(x in e.code for x in ['handler', 'read_', 'modified_'])]
    print(f"Functional affect validation errors: {len(functional_errors)}")
    for error in functional_errors:
        print(f"  {error.code}: {error.message}")

    assert len(functional_errors) == 4
    error_messages = [e.message for e in functional_errors]
    assert any('invalid_handler' in msg for msg in error_messages)
    assert any('unknown_read_var' in msg for msg in error_messages)
    assert any('unknown_read_param' in msg for msg in error_messages)
    assert any('unknown_mod_param' in msg for msg in error_messages)
    print("✓ FunctionalAffect validation test passed\n")


def test_discrete_parameters_validation():
    """Test that discrete_parameters in coupling entries are validated."""
    print("=== Test 3: discrete_parameters validation ===")

    test_coupling = CouplingEntry(
        coupling_type=CouplingType.EVENT,
        discrete_parameters=['valid_param', 'invalid_param', 'rs_param']  # valid_param and rs_param exist, invalid_param doesn't
    )

    test_model = Model(
        name='test_model',
        variables={
            'x': ModelVariable(type='state'),
            'valid_param': ModelVariable(type='parameter')
        },
        equations=[{'lhs': 'dx_dt', 'rhs': 1.0}]
    )

    test_rs = ReactionSystem(
        name='test_rs',
        species=[Species(name='A')],
        parameters=[Parameter(name='rs_param', value=1.0)],
        reactions=[]
    )

    test_file = EsmFile(
        version='1.0',
        metadata=Metadata(title='test discrete_parameters'),
        models={'test_model': test_model},
        reaction_systems={'test_rs': test_rs},
        coupling=[test_coupling]
    )

    result = validate(test_file)

    # Should have exactly 1 error for invalid_param
    discrete_param_errors = [e for e in result.structural_errors if 'discrete_parameter' in e.code]
    print(f"discrete_parameters validation errors: {len(discrete_param_errors)}")
    for error in discrete_param_errors:
        print(f"  {error.code}: {error.message}")

    assert len(discrete_param_errors) == 1
    assert 'invalid_param' in discrete_param_errors[0].message
    print("✓ discrete_parameters validation test passed\n")


def test_functional_affect_in_affect_neg():
    """Test that FunctionalAffect in affect_neg is also validated."""
    print("=== Test 4: FunctionalAffect in affect_neg validation ===")

    test_event = ContinuousEvent(
        name='test_event',
        conditions=[{'op': 'gt', 'args': ['t', 1.0]}],
        affects=[AffectEquation(lhs='x', rhs=2.0)],
        affect_neg=[
            FunctionalAffect(
                handler_id='invalid_handler',  # This handler doesn't exist
                read_vars=['unknown_var'],  # This variable doesn't exist
                read_params=['unknown_param'],  # This parameter doesn't exist
                modified_params=['unknown_mod_param']  # This parameter doesn't exist
            )
        ]
    )

    test_model = Model(
        name='test_model',
        variables={'x': ModelVariable(type='state')},
        equations=[{'lhs': 'dx_dt', 'rhs': 1.0}]
    )

    test_file = EsmFile(
        version='1.0',
        metadata=Metadata(title='test functional affects in affect_neg'),
        models={'test_model': test_model},
        events=[test_event]
    )

    result = validate(test_file)

    # Should have 4 errors for affect_neg functional affect validation
    functional_errors = [e for e in result.structural_errors if any(x in e.code for x in ['handler', 'read_', 'modified_'])]
    print(f"affect_neg FunctionalAffect validation errors: {len(functional_errors)}")
    for error in functional_errors:
        print(f"  {error.code}: {error.message}")

    assert len(functional_errors) == 4
    # All errors should mention affect_neg in the message
    for error in functional_errors:
        assert 'Affect_neg' in error.message
    print("✓ FunctionalAffect in affect_neg validation test passed\n")


def test_all_validations_pass():
    """Test that validation passes when all references are valid."""
    print("=== Test 5: All validations pass ===")

    test_event = ContinuousEvent(
        name='test_event',
        conditions=[{'op': 'gt', 'args': ['t', 1.0]}],
        affects=[
            AffectEquation(lhs='x', rhs=2.0),
            FunctionalAffect(
                handler_id='valid_handler',
                read_vars=['x', 'y'],
                read_params=['p1'],
                modified_params=['p2']
            )
        ],
        affect_neg=[
            AffectEquation(lhs='y', rhs=3.0),
            FunctionalAffect(
                handler_id='valid_handler',
                read_vars=['x'],
                read_params=['p1', 'p2'],
                modified_params=['p1']
            )
        ]
    )

    test_coupling = CouplingEntry(
        coupling_type=CouplingType.EVENT,
        discrete_parameters=['p1', 'p2', 'rs_param']
    )

    test_model = Model(
        name='test_model',
        variables={
            'x': ModelVariable(type='state'),
            'y': ModelVariable(type='state'),
            'p1': ModelVariable(type='parameter'),
            'p2': ModelVariable(type='parameter')
        },
        equations=[
            {'lhs': 'dx_dt', 'rhs': 1.0},
            {'lhs': 'dy_dt', 'rhs': 1.0}
        ]
    )

    test_rs = ReactionSystem(
        name='test_rs',
        species=[Species(name='A')],
        parameters=[Parameter(name='rs_param', value=1.0)],
        reactions=[]
    )

    test_operator = Operator(operator_id='valid_handler')

    test_file = EsmFile(
        version='1.0',
        metadata=Metadata(title='test all pass'),
        models={'test_model': test_model},
        reaction_systems={'test_rs': test_rs},
        events=[test_event],
        operators=[test_operator],
        coupling=[test_coupling]
    )

    result = validate(test_file)

    # Should have no errors related to the new validations
    event_errors = [e for e in result.structural_errors
                   if any(x in e.code for x in ['affect', 'handler', 'read_', 'modified_', 'discrete_parameter'])]
    print(f"Event-related validation errors: {len(event_errors)}")
    for error in event_errors:
        print(f"  {error.code}: {error.message}")

    assert len(event_errors) == 0
    print("✓ All validations pass test passed\n")


if __name__ == "__main__":
    print("Testing enhanced event validation for task EarthSciSerialization-rr42\n")

    test_affect_neg_validation()
    test_functional_affect_validation()
    test_discrete_parameters_validation()
    test_functional_affect_in_affect_neg()
    test_all_validations_pass()

    print("🎉 All tests passed! Enhanced event validation is working correctly.")
    print("\nFixed validation issues:")
    print("✓ affect_neg variables (direction-dependent affects) are now validated")
    print("✓ FunctionalAffect parameters (handler_id, read_vars, read_params, modified_params) are now validated")
    print("✓ discrete_parameters in coupling entries are now validated")
    print("✓ FunctionalAffect validation works in both affects and affect_neg")