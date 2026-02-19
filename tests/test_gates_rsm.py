from prime_directive.validators.rsm_color import validate_rsm_color


def test_rsm_requires_color_profile():
    assert not validate_rsm_color({}).passed
