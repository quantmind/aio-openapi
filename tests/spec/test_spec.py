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


async def test_spec_security(test_app):
    open_api = OpenApi(
        security=dict(
            auth_key={
                'type': 'apiKey',
                'name': 'X-Api-Key',
                'description': 'The authentication key',
                'in': 'header'
            }
        )
    )
    spec = OpenApiSpec(asdict(open_api))
    spec.build(test_app)
    assert spec.doc['info']['security'] == ['auth_key']
    assert spec.doc['components']['securitySchemes']


async def test_spec_422(test_app):
    open_api = OpenApi()
    spec = OpenApiSpec(asdict(open_api))
    spec.build(test_app)
    tasks = spec.doc['paths']['/tasks']
    resp = tasks['post']['responses']
    assert (
        resp[422]['content']['application/json']['schema']['$ref'] ==
        '#/components/schemas/ValidationErrors'
    )
