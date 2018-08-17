import pytest

from openapi.rest import rest
from openapi.spec import OpenApi, OpenApiSpec
from openapi.spec.exceptions import InvalidSpecException

#  from openapi_spec_validator import validate_spec

from ..example import endpoints


def create_spec_app(routes):
    def setup_app(app):
        app.router.add_routes(routes)

    cli = rest(setup_app=setup_app)
    app = cli.web()
    return app


def test_init():
    u = OpenApi()
    assert u.version == '0.1.0'


async def test_spec_validation(test_app):
    spec = OpenApiSpec()
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
    spec = OpenApiSpec(open_api)
    spec.build(test_app)
    assert spec.doc['info']['security'] == ['auth_key']
    assert spec.doc['components']['securitySchemes']


async def test_spec_422(test_app):
    spec = OpenApiSpec()
    spec.build(test_app)
    tasks = spec.doc['paths']['/tasks']
    resp = tasks['post']['responses']
    assert (
        resp[422]['content']['application/json']['schema']['$ref'] ==
        '#/components/schemas/ValidationErrors'
    )


async def test_invalid_path():
    app = create_spec_app(endpoints.invalid_path_routes)
    spec = OpenApiSpec(validate_docs=True)

    with pytest.raises(InvalidSpecException):
        spec.build(app)


async def test_invalid_method_missing_summary():
    app = create_spec_app(endpoints.invalid_method_summary_routes)
    spec = OpenApiSpec(validate_docs=True)

    with pytest.raises(InvalidSpecException):
        spec.build(app)


async def test_invalid_method_missing_description():
    app = create_spec_app(endpoints.invalid_method_description_routes)
    spec = OpenApiSpec(validate_docs=True)

    with pytest.raises(InvalidSpecException):
        spec.build(app)


async def test_allowed_tags_ok():
    app = create_spec_app(endpoints.routes)
    spec = OpenApiSpec(
        allowed_tags=set(('Task', 'Transaction', 'Random'))
    )
    spec.build(app)


async def test_allowed_tags_invalid():
    app = create_spec_app(endpoints.routes)
    spec = OpenApiSpec(
        validate_docs=True,
        allowed_tags=set(('Task', 'Transaction'))
    )
    with pytest.raises(InvalidSpecException):
        spec.build(app)


async def test_tags_missing_description():
    app = create_spec_app(endpoints.invalid_tag_missing_description_routes)
    spec = OpenApiSpec(
        validate_docs=True,
        allowed_tags=set(('Task', 'Transaction', 'Random'))
    )
    with pytest.raises(InvalidSpecException):
        spec.build(app)
