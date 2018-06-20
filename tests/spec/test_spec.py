from dataclasses import asdict

#  from openapi_spec_validator import validate_spec

from openapi.spec import OpenApi, OpenApiSpec


def test_init():
    u = OpenApi()
    assert u.version == '0.1.0'


async def test_spec_validation(test_app):
    open_api = OpenApi()

    spec = OpenApiSpec(asdict(open_api))
    spec.build(test_app)
    # validate_spec(spec.doc)
