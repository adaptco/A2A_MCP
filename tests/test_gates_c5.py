from prime_directive.validators.c5_geometry import validate_c5_geometry


def test_c5_requires_geometry_field():
    assert not validate_c5_geometry({}).passed
