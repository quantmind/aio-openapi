import pytest

from openapi.exc import InvalidSpecException
from openapi.rest import rest
from openapi.spec import OpenApi, OpenApiSpec
from openapi.testing import json_body
from tests.example import endpoints, endpoints_additional


def create_spec_app(routes):
    def setup_app(app):
        app.router.add_routes(routes)

    cli = rest(setup_app=setup_app)
    app = cli.web()
    return app


def test_init():
    u = OpenApi()
    assert u.version == "0.1.0"


async def test_spec_validation(test_app):
    spec = OpenApiSpec()
    spec.build(test_app)
    # validate_spec(spec.doc)


async def test_spec_422(test_app):
    spec = OpenApiSpec()
    spec.build(test_app)
    tasks = spec.doc["paths"]["/tasks"]
    resp = tasks["post"]["responses"]
    assert (
        resp[422]["content"]["application/json"]["schema"]["$ref"]
        == "#/components/schemas/ValidationErrors"
    )


async def test_invalid_path():
    app = create_spec_app(endpoints_additional.invalid_path_routes)
    spec = OpenApiSpec(validate_docs=True)

    with pytest.raises(InvalidSpecException):
        spec.build(app)


async def test_invalid_method_missing_summary():
    app = create_spec_app(endpoints_additional.invalid_method_summary_routes)
    spec = OpenApiSpec(validate_docs=True)

    with pytest.raises(InvalidSpecException):
        spec.build(app)


async def test_invalid_method_missing_description():
    app = create_spec_app(endpoints_additional.invalid_method_description_routes)
    spec = OpenApiSpec(validate_docs=True)

    with pytest.raises(InvalidSpecException):
        spec.build(app)


async def test_allowed_tags_ok():
    app = create_spec_app(endpoints.routes)
    spec = OpenApiSpec(allowed_tags=set(("Task", "Transaction", "Random")))
    spec.build(app)


async def test_allowed_tags_invalid():
    app = create_spec_app(endpoints.routes)
    spec = OpenApiSpec(validate_docs=True, allowed_tags=set(("Task", "Transaction")))
    with pytest.raises(InvalidSpecException):
        spec.build(app)


async def test_tags_missing_description():
    app = create_spec_app(endpoints_additional.invalid_tag_missing_description_routes)
    spec = OpenApiSpec(
        validate_docs=True, allowed_tags=set(("Task", "Transaction", "Random"))
    )
    with pytest.raises(InvalidSpecException):
        spec.build(app)


async def test_spec_root(cli):
    response = await cli.get("/spec")
    spec = await json_body(response)
    assert "paths" in spec
    assert "tags" in spec
    assert len(spec["tags"]) == 5
    assert spec["tags"][3]["name"] == "Task"
    assert spec["tags"][3]["description"] == "Simple description"
