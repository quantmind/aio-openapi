import json
import tempfile

from dataclasses import asdict
from pyswagger import App

from openapi.rest import rest
from openapi.spec import OpenApi, OpenApiSpec


def test_init():
    u = OpenApi()
    assert u.version == '0.1.0'


async def test_spec_validation():
    openapi_app = rest().web()
    open_api = OpenApi()

    spec = OpenApiSpec(asdict(open_api))
    spec.build(openapi_app)
    with tempfile.NamedTemporaryFile('w+', suffix='.json') as temp_file:
        temp_file.write(json.dumps(spec.doc))
        temp_file.seek(0)
        app = App.create('file://'+temp_file.name)
        errors = app.validate()
        assert len(errors) == 0
