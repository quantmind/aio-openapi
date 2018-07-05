from collections import OrderedDict
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List

from aiohttp import hdrs
from aiohttp import web
from dataclasses import dataclass, asdict, is_dataclass

from .exceptions import InvalidTypeException
from .path import ApiPath
from .utils import load_yaml_from_docstring, trim_docstring
from ..data import fields
from ..utils import compact, is_subclass

OPENAPI = '3.0.1'
METHODS = [method.lower() for method in hdrs.METH_ALL]
SCHEMA_BASE_REF = '#/components/schemas/'


@dataclass
class Contact:
    name: str = "API Support"
    url: str = "http://www.example.com/support"
    email: str = "support@example.com"


@dataclass
class License:
    name: str = "Apache 2.0"
    url: str = "https://www.apache.org/licenses/LICENSE-2.0.html"


@dataclass
class OpenApi:
    title: str = 'Open API'
    description: str = ''
    version: str = '0.1.0'
    termsOfService: str = ''
    contact: Contact = Contact()
    license: License = License()


class SchemaParser:

    _fields_mapping = {
        str: {'type': 'string'},
        int: {'type': 'integer', fields.FORMAT: 'int32'},
        float: {'type': 'number', fields.FORMAT: 'float'},
        bool: {'type': 'boolean'},
        datetime: {'type': 'string', fields.FORMAT: 'date-time'},
        Decimal: {'type': 'number'}
    }

    parsed_schemas = {}

    def __init__(self, schemas_to_parse):
        self._schemas_to_parse = set(schemas_to_parse)

    def parse(self):
        for schema in self._schemas_to_parse:
            if schema.__name__ in self.parsed_schemas:
                continue

            parsed_schema = self._schema2json(schema)
            self.parsed_schemas[schema.__name__] = parsed_schema
        return self.parsed_schemas

    def field2json(self, field):
        field = fields.as_field(field)
        mapping = self._fields_mapping.get(field.type, None)
        enum = None
        if not mapping:
            if is_subclass(field.type, Enum):
                mapping = dict(type='string')
                enum = [e.name for e in field.type]
            elif is_subclass(field.type, List):
                return self._list2json(field.type)
            elif is_dataclass(field.type):
                return self._get_schema_ref(field.type)
            else:
                raise InvalidTypeException(field.type)

        json_property = {'type': mapping['type']}
        meta = field.metadata
        if meta.get(fields.DESCRIPTION):
            json_property['description'] = meta.get(fields.DESCRIPTION)
        fmt = meta.get(fields.FORMAT) or mapping.get(fields.FORMAT, None)
        if fmt:
            json_property[fields.FORMAT] = fmt
        if enum:
            json_property['enum'] = enum
        validator = meta.get(fields.VALIDATOR)
        # add additional parameters fields from validators
        if isinstance(validator, fields.Validator):
            validator.openapi(json_property)
        return json_property

    def _schema2json(self, schema):
        properties = {}
        required = []
        for item in schema.__dataclass_fields__.values():
            if item.metadata.get(fields.REQUIRED, False):
                required.append(item.name)
            json_property = self.field2json(item)
            if not json_property:
                continue
            for name in fields.field_ops(item):
                properties[name] = json_property

        return {
            'type': 'object',
            'description': trim_docstring(schema.__doc__),
            'properties': properties,
            'required': required,
            'additionalProperties': False
        }

    def _get_schema_ref(self, schema):
        if schema not in self.parsed_schemas:
            parsed_schema = self._schema2json(schema)
            self.parsed_schemas[schema.__name__] = parsed_schema

        return {'$ref': SCHEMA_BASE_REF + schema.__name__}

    def _list2json(self, field_type):
        return {
            'type': 'array',
            'items': self.field2json(field_type.__args__[0])
        }


class OpenApiSpec:
    """Open API document builder
    """
    def __init__(self, info, default_content_type=None,
                 default_responses=None):
        self.schemas = {}
        self.parameters = {}
        self.responses = {}
        self.tags = {}
        self.plugins = {}
        self.servers = []
        self.default_content_type = default_content_type or 'application/json'
        self.default_responses = default_responses or {}
        self.doc = dict(
            openapi=OPENAPI,
            info=info,
            paths=OrderedDict()
        )
        self.schemas_to_parse = set()

    @property
    def paths(self):
        return self.doc['paths']

    def build(self, app):
        """Build the ``doc`` dictionary by adding paths
        """
        self.logger = app.logger
        self.schemas_to_parse.add(app['exc_schema'])
        self._build_paths(app)
        schemas_parser = SchemaParser(self.schemas_to_parse)
        self.schemas = schemas_parser.parse()
        s = self.schemas
        p = self.parameters
        r = self.responses
        doc = self.doc
        doc.update(compact(
            tags=[self.tags[name] for name in sorted(self.tags)],
            components=compact(
                schemas=OrderedDict(((k, s[k]) for k in sorted(s))),
                parameters=OrderedDict(((k, p[k]) for k in sorted(p))),
                responses=OrderedDict(((k, r[k]) for k in sorted(r))),
            ),
            servers=self.servers
        ))
        return self

    def _build_paths(self, app):
        """Loop through app paths and add
        schemas, parameters and paths objects to the spec
        """
        paths = self.paths
        routes = app.router.routes()
        for route in routes:
            route_info = route.get_info()
            path = route_info.get('path', route_info.get('formatter', None))
            handler = route.handler
            if issubclass(handler, ApiPath) and not handler.private:
                paths[path] = self._build_path_object(handler, app)

    def _build_path_object(self, handler, path_obj):
        path_obj = load_yaml_from_docstring(handler.__doc__) or {}
        tags = self._extend_tags(path_obj.pop('tags', None))
        for method in METHODS:
            method_handler = getattr(handler, method, None)
            if method_handler is None:
                continue

            operation = getattr(method_handler, 'op', None)
            if operation is None:
                self.logger.warning(
                    'No operation defined for %s.%s', handler.__name__, method
                )
                continue

            method_doc = load_yaml_from_docstring(method_handler.__doc__) or {}
            mtags = tags.copy()
            mtags.update(self._extend_tags(method_doc.pop('tags', None)))
            op_attrs = asdict(operation)
            self._add_schemas_from_operation(op_attrs)
            responses = self._get_resonse_object(op_attrs, method_doc)
            request_body = self._get_request_body_object(op_attrs, method_doc)

            method_doc['tags'] = list(mtags)
            path_obj[method] = method_doc

            if responses is not None:
                path_obj[method]['responses'] = responses

            if request_body is not None:
                path_obj[method]['requestBody'] = request_body

        return path_obj

    def _get_resonse_object(self, op_attrs, method_doc):
        response_schema = op_attrs.get('response_schema', None)
        if response_schema is None:
            return None

        schema = {}
        if type(response_schema) == list:
            schema['type'] = 'array'
            schema['items'] = {
                '$ref': SCHEMA_BASE_REF + response_schema[0].__name__
            }
        elif response_schema is not None:
            schema['$ref'] = SCHEMA_BASE_REF + response_schema.__name__

        responses = {}
        for response, data in method_doc.get('responses', {}).items():
            responses[response] = {
                'description': data['description'],
                'content': {
                    'application/json': {
                        'schema': schema
                    }
                }
            }
        return responses

    def _get_request_body_object(self, op_attrs, method_doc):
        body_schema = op_attrs.get('body_schema', None)
        if body_schema is None:
            return

        if type(body_schema) == list:
            body_schema = body_schema[0]

        return {
            'description': method_doc.get('body', {}).get('summary', ''),
            'content': {
                'application/json': {
                    'schema': SCHEMA_BASE_REF + body_schema.__name__
                }
            }
        }

    def _add_schemas_from_operation(self, operation_obj):
        schemas = ['response_schema', 'body_schema', 'query_schema']
        for schema in schemas:
            schema_obj = operation_obj[schema]
            if schema_obj is not None:
                if type(schema_obj) == list:
                    schema_obj = schema_obj[0]
                self.schemas_to_parse.add(schema_obj)

    def _extend_tags(self, tags):
        names = set()
        for tag in (tags or ()):
            if isinstance(tag, str):
                tag = {'name': tag}
            name = tag.get('name')
            if name:
                if name not in self.tags:
                    self.tags[name] = tag
                else:
                    self.tags[name].update(tag)
                names.add(name)
        return names


async def spec_root(request):
    """Return the OpenApi spec
    """
    app = request.app
    spec = app.get('spec_doc')
    if not spec:
        spec = OpenApiSpec(asdict(app['spec']))
        app['spec_doc'] = spec.build(app)
    return web.json_response(spec.doc)
