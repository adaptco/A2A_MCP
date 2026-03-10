from monotonicity_validator import (
    INVARIANTS,
    MonotonicityValidationError,
    MonotonicityValidator,
    ValidatorMode,
)


def test_hard_reject_fails_on_any_violation() -> None:
    validator = MonotonicityValidator(mode=ValidatorMode.HARD_REJECT)

    result = validator.evaluate({**INVARIANTS, "fov": 59})

    assert result.passed is False
    assert any("fov" in violation for violation in result.violations)


def test_soft_projection_passes_and_repairs_drift() -> None:
    validator = MonotonicityValidator(mode=ValidatorMode.SOFT_PROJECTION)

    result = validator.evaluate({**INVARIANTS, "wheel_spokes": 6})

    assert result.passed is True
    assert result.projected_state["wheel_spokes"] == INVARIANTS["wheel_spokes"]


def test_hybrid_rejects_structural_drift() -> None:
    validator = MonotonicityValidator(mode=ValidatorMode.HYBRID)

    result = validator.evaluate({"wheel_spokes": 5})

    assert result.passed is False
    assert any("missing invariant field" in violation for violation in result.violations)


def test_enforce_raises_when_validation_fails() -> None:
    validator = MonotonicityValidator(mode=ValidatorMode.HARD_REJECT)

    try:
        validator.enforce({**INVARIANTS, "body_color": "blue"})
    except MonotonicityValidationError as exc:
        assert "body_color" in str(exc)
    else:
        raise AssertionError("expected MonotonicityValidationError")
