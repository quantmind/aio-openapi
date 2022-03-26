import os
from collections import OrderedDict
from dataclasses import MISSING, Field, asdict, dataclass, field
from dataclasses import fields as get_fields
from dataclasses import is_dataclass
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Set, Type, Union, cast

from aiohttp import hdrs, web

from ..data import fields
from ..data.exc import ErrorMessage, FieldError, ValidationErrors, error_response_schema
from ..exc import InvalidSpecException, InvalidTypeException
from ..utils import TypingInfo, compact, is_subclass
from .path import ApiPath
from .redoc import Redoc
from .server import default_server
from .utils import load_yaml_from_docstring, trim_docstring

OPENAPI = "3.0.3"
METHODS = [method.lower() for method in hdrs.METH_ALL]
SCHEMAS_TO_SCHEMA = ("response_schema", "body_schema")
SCHEMA_BASE_REF = "#/components/schemas/"

EMPTY_DEFAULTS = frozenset((None, MISSING, ""))
SPEC_ROUTE = os.environ.get("SPEC_ROUTE", "/spec")


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
    title: str = "Open API"
    description: str = ""
    version: str = "0.1.0"
    termsOfService: str = ""
    contact: Contact = Contact()
    license: License = License()


@dataclass
class OpenApiSpec:
    """Open API Specification"""

    info: OpenApi = field(default_factory=OpenApi)
    default_content_type: str = "application/json"
    default_responses: Dict = field(default_factory=dict)
    security: Dict = field(default_factory=dict)
    servers: List[Dict] = field(default_factory=list)
    validate_docs: bool = False
    allowed_tags: Set = field(default_factory=set)
    spec_url: str = SPEC_ROUTE
    redoc: Optional[Redoc] = None

    def routes(self, request: web.Request) -> Iterable:
        """Routes to include in the spec"""
        return request.app.router.routes()

    def setup_app(self, app: web.Application):
        app["spec"] = self
        app.router.add_get(self.spec_url, self.spec_route, name="openapi_spec")
        if self.redoc:
            app.router.add_get(self.redoc.path, self.redoc.handle_doc)

    def spec_route(self, request: web.Request) -> web.Response:
        """Return the OpenApi spec"""
        return web.json_response(self.build(request))

    def build(self, request: web.Request) -> Dict:
        doc = SpecDoc(request, self)
        security = self.security.copy()
        servers = self.servers[:] if self.servers else []
        return doc(security, servers)


class SchemaParser:
    """Utility class for parsing schemas"""

    def __init__(self, validate_docs: bool = False) -> None:
        self.validate_docs = validate_docs
        self.schemas_to_parse: Dict[str, type] = {}

    def get_parameters(self, schema: Any, default_in: str = "path") -> List:
        """Extract parameters list from a dataclass schema"""
        params = []
        json_schema = self.dataclass2json(schema)
        required = set(json_schema.get("required", ()))
        for name, entry in json_schema["properties"].items():
            entry = compact(
                name=name,
                description=entry.pop("description", None),
                schema=entry,
                required=name in required,
            )
            entry["in"] = default_in
            params.append(entry)
        return params

    def field2json(
        self, field_or_type: Union[Type, Field], validate: bool = True
    ) -> Dict[str, dict]:
        """Convert a dataclass field to Json schema"""
        field = fields.as_field(field_or_type)
        meta = field.metadata
        items = meta.get(fields.ITEMS)
        json_property = self.get_schema_info(field.type, items=items)
        field_description = meta.get(fields.DESCRIPTION)
        if not field_description:
            if self.validate_docs and validate:
                raise InvalidSpecException(
                    f'Missing description for field "{field.name}"'
                )
        else:
            json_property["description"] = field_description
        fmt = meta.get(fields.FORMAT)
        if fmt:
            json_property[fields.FORMAT] = fmt
        self.add_default(field, json_property)
        validator = meta.get(fields.VALIDATOR)
        # add additional parameters fields from validators
        if isinstance(validator, fields.Validator):
            validator.openapi(json_property)
        return json_property

    def dataclass2json(self, schema: Any) -> Dict[str, Any]:
        """Extract the object representation of a dataclass schema"""
        type_info = cast(TypingInfo, TypingInfo.get(schema))
        if not type_info or not type_info.is_dataclass:
            raise InvalidSpecException(
                "Schema must be a dataclass, got "
                f"{type_info.element if type_info else None}"
            )
        properties = {}
        required = []
        for item in get_fields(type_info.element):
            json_property = self.field2json(item)
            field_required = json_property.pop("required", True)
            if not json_property:
                continue
            if item.metadata.get(fields.REQUIRED, field_required):
                required.append(item.name)
            for name in fields.field_ops(item):
                properties[name] = json_property

        json_schema = {
            "type": "object",
            "description": trim_docstring(schema.__doc__ or ""),
            "properties": properties,
            "additionalProperties": False,
        }
        if required:
            json_schema["required"] = required
        return json_schema

    schema2json = dataclass2json
    # for backward compatibility

    def get_schema_info(
        self, schema: Any, items: Optional[Field] = None
    ) -> Dict[str, Any]:
        type_info = cast(TypingInfo, TypingInfo.get(schema))
        if type_info.container is list:
            return {
                "type": "array",
                "items": {"type": "object", "additionalProperties": True}
                if type_info.element is Any
                else self.field2json(
                    fields.as_field(type_info.element, field=items), False
                ),
            }
        elif type_info.container is dict:
            return {
                "type": "object",
                "additionalProperties": True
                if type_info.element is Any
                else self.field2json(
                    fields.as_field(type_info.element, field=items), False
                ),
            }
        elif type_info.is_union:
            required = True
            one_of = []
            for e in type_info.element:
                if e.is_none:
                    required = False
                else:
                    one_of.append(self.get_schema_info(e))
            info = one_of[0] if len(one_of) == 1 else {"oneOf": one_of}
            info["required"] = required
            return info
        elif type_info.is_dataclass:
            name = self.add_schema_to_parse(type_info.element)
            return {"$ref": f"{SCHEMA_BASE_REF}{name}"}
        else:
            return self.get_primitive_info(type_info.element)

    def get_primitive_info(self, schema: Type) -> Dict[str, Any]:
        mapping = fields.PRIMITIVE_TYPES.get(schema)
        if not mapping:
            if is_subclass(schema, Enum):
                enum_type = cast(Type[Enum], schema)
                return {"type": "string", "enum": [e.name for e in enum_type]}
            else:
                raise InvalidTypeException(f"Cannot understand {schema} while parsing")
        return dict(mapping)

    def add_schema_to_parse(self, schema: type) -> str:
        if not is_dataclass(schema):
            raise InvalidTypeException(f"Schema must be a dataclass, got {schema}")
        name = schema.__name__
        self.schemas_to_parse[name] = schema
        return name

    def parsed_schemas(self) -> Dict[str, Dict]:
        parsed = {}
        while self.schemas_to_parse:
            to_parse = self.schemas_to_parse
            self.schemas_to_parse = {}
            parsed.update(
                (
                    (name, self.dataclass2json(schema))
                    for name, schema in to_parse.items()
                )
            )
        return parsed

    def add_default(self, field: Field, json_property: Dict):
        if field.default in EMPTY_DEFAULTS or field.metadata.get(fields.REQUIRED):
            return
        default = field.default
        type_info = TypingInfo.get(field.type)
        if type_info.element not in fields.PRIMITIVE_TYPES:
            if is_subclass(type_info.element, Enum) and isinstance(
                default, type_info.element
            ):
                default = default.name
            else:
                return
        json_property["default"] = default


class SpecDoc(SchemaParser):
    """Build the OpenAPI Spec doc"""

    def __init__(
        self,
        request: web.Request,
        spec: OpenApiSpec,
        public: bool = True,
        private: bool = False,
    ) -> None:
        super().__init__(spec.validate_docs)
        self.request: web.Request = request
        self.spec: OpenApiSpec = spec
        self.logger = request.app.logger
        self.public: bool = public
        self.private: bool = private
        self.parameters: Dict = {}
        self.responses: Dict = {}
        self.tags: Dict = {}
        self.plugins: Dict = {}
        self.doc: Dict = dict(
            openapi=OPENAPI,
            info=asdict(self.spec.info or OpenApi()),
            paths=OrderedDict(),
        )

    @property
    def app(self) -> web.Application:
        return self.request.app

    def __call__(self, security: Dict, servers: List) -> Dict:
        # Add errors schemas
        self.add_schema_to_parse(ValidationErrors)
        self.add_schema_to_parse(ErrorMessage)
        self.add_schema_to_parse(FieldError)
        self.doc["security"] = [
            {name: value.pop("scopes", [])} for name, value in security.items()
        ]
        # Build paths
        self._build_paths()
        s = self.parsed_schemas()
        p = self.parameters
        r = self.responses
        doc = self.doc
        doc.update(
            compact(
                tags=[self.tags[name] for name in sorted(self.tags)],
                components=compact(
                    schemas=OrderedDict(((k, s[k]) for k in sorted(s))),
                    parameters=OrderedDict(((k, p[k]) for k in sorted(p))),
                    responses=OrderedDict(((k, r[k]) for k in sorted(r))),
                    securitySchemes=OrderedDict(
                        (((k, security[k]) for k in sorted(security)))
                    ),
                ),
                servers=servers,
            )
        )
        if not doc.get("servers"):
            # build the server info
            doc["servers"] = [default_server(self.request)]
        return doc

    # Internals

    def _build_paths(self) -> None:
        """Loop through app paths and add
        schemas, parameters and paths objects to the spec
        """
        paths = self.doc["paths"]
        base_path = self.app["cli"].base_path
        for route in self.spec.routes(self.request):
            route_info = route.get_info()
            path = route_info.get("path", route_info.get("formatter", None))
            handler = route.handler
            if is_subclass(handler, ApiPath) and self._include(handler.private):
                N = len(base_path)
                path = path[N:]
                paths[path] = self._build_path_object(path, handler)

        if self.validate_docs:
            self._validate_tags()

    def _validate_tags(self) -> None:
        for tag_name, tag_obj in self.tags.items():
            if self.spec.allowed_tags and tag_name not in self.spec.allowed_tags:
                raise InvalidSpecException(f'Tag "{tag_name}" not allowed')
            if "description" not in tag_obj:
                raise InvalidSpecException(f'Missing tag "{tag_name}" description')

    def _build_path_object(self, path: str, handler):
        path_obj = load_yaml_from_docstring(handler.__doc__) or {}
        doc_tags = path_obj.pop("tags", None)
        if not doc_tags and self.validate_docs:
            raise InvalidSpecException(f"Missing tags docstring for route '{path}'")

        tags = self._extend_tags(doc_tags)
        if handler.path_schema:
            path_obj["parameters"] = self.get_parameters(handler.path_schema)
        for method in METHODS:
            try:
                method_handler = getattr(handler, method, None)
                if method_handler is None:
                    continue

                operation = getattr(method_handler, "op", None)
                if operation is None:
                    self.logger.warning(
                        "No operation defined for %s.%s", handler.__name__, method
                    )
                    continue

                method_doc = load_yaml_from_docstring(method_handler.__doc__) or {}
                if not self._include(method_doc.pop("private", self.private)):
                    continue
                mtags = tags.copy()
                mtags.update(self._extend_tags(method_doc.pop("tags", None)))
                self._get_response_object(operation.response_schema, method_doc)
                self._get_request_body_object(operation.body_schema, method_doc)
                self._get_query_parameters(operation.query_schema, method_doc)
                method_info = self._get_method_info(method_handler, method_doc)
                method_doc.update(method_info)
                method_doc["tags"] = list(mtags)
                path_obj[method] = method_doc
            except (InvalidSpecException, InvalidTypeException) as exc:
                raise InvalidSpecException(
                    f"Invalid spec in route '{method} {path}': {exc}"
                ) from None

        return path_obj

    def _get_method_info(self, method_handler, method_doc):
        summary = method_doc.get("summary", "")
        description = method_doc.get("description", "")
        if self.validate_docs:
            if not summary:
                raise InvalidSpecException(
                    f'Missing method summary for "{method_handler}"'
                )
            if not description:
                raise InvalidSpecException(
                    f'Missing method description for "{method_handler}"'
                )
        return {"summary": summary, "description": description}

    def _get_response_object(
        self, type_info: Optional[TypingInfo], doc: Dict[str, str]
    ) -> None:
        if type_info:
            schema = self.get_schema_info(type_info)
            responses = {}
            for response, data in doc.get("responses", {}).items():
                rschema = schema
                if response >= 400:
                    rschema = self.get_schema_info(error_response_schema(response))
                content = data.get("content", self.spec.default_content_type)
                responses[response] = {
                    "description": data.get("description", ""),
                    "content": {content: {"schema": rschema}},
                }
            doc["responses"] = responses

    def _get_request_body_object(
        self, type_info: Optional[TypingInfo], doc: Dict[str, str]
    ) -> None:
        if type_info:
            content = doc.pop("body_content", self.spec.default_content_type)
            schema = self.get_schema_info(type_info)
            doc["requestBody"] = {"content": {content: {"schema": schema}}}

    def _get_query_parameters(
        self, type_info: Optional[TypingInfo], doc: Dict[str, str]
    ) -> None:
        if type_info:
            doc["parameters"] = self.get_parameters(type_info, "query")

    def _extend_tags(self, tags):
        names = set()
        for tag in tags or ():
            if isinstance(tag, str):
                tag = {"name": tag}
            name = tag.get("name")
            if name:
                if name not in self.tags:
                    self.tags[name] = tag
                else:
                    self.tags[name].update(tag)
                names.add(name)
        return names

    def _include(self, is_private: bool) -> bool:
        return (is_private and self.private) or (not is_private and self.public)
