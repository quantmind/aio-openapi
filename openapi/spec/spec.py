from collections import OrderedDict
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Dict

from aiohttp import hdrs
from aiohttp import web
from dataclasses import dataclass, asdict, is_dataclass, field

from .exceptions import InvalidTypeException
from .path import ApiPath
from .utils import load_yaml_from_docstring, trim_docstring
from ..data import fields
from ..data.exc import (
    ValidationErrors, ErrorMessage, FieldError, error_response_schema
)
from ..utils import compact, is_subclass

OPENAPI = '3.0.1'
METHODS = [method.lower() for method in hdrs.METH_ALL]
SCHEMAS_TO_SCHEMA = ('response_schema', 'body_schema')
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
    security: Dict[str, Dict] = field(default_factory=dict)
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

    def __init__(self, group=None):
        self.group = group or SchemaGroup()

    def parameters(self, Schema, default_in='path'):
        params = []
        schema = self.schema2json(Schema)
        required = set(schema['required'])
        for name, entry in schema['properties'].items():
            entry = compact(
                name=name,
                description=entry.pop('description', None),
                schema=entry,
                required=name in required
            )
            entry['in'] = default_in
            params.append(entry)
        return params

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
            elif is_subclass(field.type, Dict):
                return self._map2json(field.type)
            elif is_dataclass(field.type):
                return self.get_schema_ref(field.type)
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

    def schema2json(self, schema):
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

    def get_schema_ref(self, schema):
        if schema not in self.group.parsed_schemas:
            parsed_schema = self.schema2json(schema)
            self.group.parsed_schemas[schema.__name__] = parsed_schema

        return {'$ref': SCHEMA_BASE_REF + schema.__name__}

    def _list2json(self, field_type):
        return {
            'type': 'array',
            'items': self.field2json(field_type.__args__[0])
        }

    def _map2json(self, field_type):
        args = field_type.__args__
        spec = {
            'type': 'object'
        }
        if args:
            if len(args) != 2 or args[0] != str:
                raise InvalidTypeException(field_type)
            spec['additionalProperties'] = self.field2json(args[1])
        return spec


class SchemaGroup:

    def __init__(self):
        self.parsed_schemas = {}

    def parse(self, schemas):
        for schema in set(schemas):
            if schema.__name__ in self.parsed_schemas:
                continue

            parsed_schema = SchemaParser(self).schema2json(schema)
            self.parsed_schemas[schema.__name__] = parsed_schema
        return self.parsed_schemas


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

    def build(self, app, public=True, private=False):
        """Build the ``doc`` dictionary by adding paths
        """
        self.logger = app.logger
        self.schemas_to_parse.add(ValidationErrors)
        self.schemas_to_parse.add(ErrorMessage)
        self.schemas_to_parse.add(FieldError)
        security = self.doc['info'].get('security')
        sk = {}
        if security:
            sk = security
            self.doc['info']['security'] = list(sk)
        self._build_paths(app, public, private)
        self.schemas = SchemaGroup().parse(self.schemas_to_parse)
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
                securitySchemes=OrderedDict((((k, sk[k]) for k in sorted(sk))))
            ),
            servers=self.servers
        ))
        return self

    def _build_paths(self, app, public, private):
        """Loop through app paths and add
        schemas, parameters and paths objects to the spec
        """
        paths = self.paths
        routes = app.router.routes()
        for route in routes:
            route_info = route.get_info()
            path = route_info.get('path', route_info.get('formatter', None))
            handler = route.handler
            if (issubclass(handler, ApiPath) and
                    self._include(handler.private, public, private)):
                paths[path] = self._build_path_object(
                    handler, app, public, private
                )

    def _build_path_object(self, handler, path_obj, public, private):
        path_obj = load_yaml_from_docstring(handler.__doc__) or {}
        tags = self._extend_tags(path_obj.pop('tags', None))
        if handler.path_schema:
            p = SchemaParser()
            path_obj['parameters'] = p.parameters(handler.path_schema)
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
            if not self._include(
                    method_doc.pop('private', private), public, private):
                continue
            mtags = tags.copy()
            mtags.update(self._extend_tags(method_doc.pop('tags', None)))
            op_attrs = asdict(operation)
            self._add_schemas_from_operation(op_attrs)
            self._get_response_object(op_attrs, method_doc)
            self._get_request_body_object(op_attrs, method_doc)
            self._get_query_parameters(op_attrs, method_doc)
            method_doc['tags'] = list(mtags)
            path_obj[method] = method_doc

        return path_obj

    def _get_schema_info(self, schema):
        info = {}
        if type(schema) == list:
            info['type'] = 'array'
            info['items'] = {
                '$ref': f'{SCHEMA_BASE_REF}{schema[0].__name__}'
            }
        elif schema is not None:
            info['$ref'] = f'{SCHEMA_BASE_REF}{schema.__name__}'
        return info

    def _get_response_object(self, op_attrs, doc):
        response_schema = op_attrs.get('response_schema', None)
        if response_schema is None:
            return None
        schema = self._get_schema_info(response_schema)
        responses = {}
        for response, data in doc.get('responses', {}).items():
            rschema = schema
            if response >= 400:
                rschema = self._get_schema_info(
                    error_response_schema(response)
                )
            responses[response] = {
                'description': data['description'],
                'content': {
                    'application/json': {
                        'schema': rschema
                    }
                }
            }
        doc['responses'] = responses

    def _get_request_body_object(self, op_attrs, doc):
        schema = self._get_schema_info(op_attrs.get('body_schema', None))
        if schema:
            doc['requestBody'] = {
                'content': {
                    'application/json': {
                        'schema': schema
                    }
                }
            }

    def _get_query_parameters(self, op_attrs, doc):
        schema = op_attrs.get('query_schema', None)
        if schema:
            doc['parameters'] = SchemaParser().parameters(schema, 'query')

    def _add_schemas_from_operation(self, operation_obj):
        for schema in SCHEMAS_TO_SCHEMA:
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

    def _include(self, is_private, public, private):
        return (
            (is_private and private) or
            (not is_private and public)
        )


async def spec_root(request):
    """Return the OpenApi spec
    """
    app = request.app
    spec = app.get('spec_doc')
    if not spec:
        spec = OpenApiSpec(asdict(app['spec']))
        app['spec_doc'] = spec.build(app)
    return web.json_response(spec.doc)
