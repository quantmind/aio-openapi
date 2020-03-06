from collections import OrderedDict
from dataclasses import Field, asdict, dataclass
from dataclasses import fields as get_fields
from dataclasses import is_dataclass
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, cast

from aiohttp import hdrs, web

from ..data import fields
from ..data.exc import ErrorMessage, FieldError, ValidationErrors, error_response_schema
from ..exc import InvalidSpecException, InvalidTypeException
from ..types import JSONType
from ..utils import TypingInfo, compact, is_subclass
from .path import ApiPath
from .server import default_server, get_spec
from .utils import load_yaml_from_docstring, trim_docstring

OPENAPI = "3.0.2"
METHODS = [method.lower() for method in hdrs.METH_ALL]
SCHEMAS_TO_SCHEMA = ("response_schema", "body_schema")
SCHEMA_BASE_REF = "#/components/schemas/"


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

    def field2json(self, field: Field, validate: bool = True) -> Dict[str, str]:
        """Convert a dataclass field to Json schema"""
        field = fields.as_field(field)
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
        validator = meta.get(fields.VALIDATOR)
        # add additional parameters fields from validators
        if isinstance(validator, fields.Validator):
            validator.openapi(json_property)
        return json_property

    def dataclass2json(self, schema: Any) -> Dict[str, str]:
        """Extract the object representation of a dataclass schema"""
        type_info = cast(TypingInfo, TypingInfo.get(schema))
        if not type_info or not type_info.is_dataclass:
            raise InvalidSpecException(
                "Schema must be a dataclass, got "
                f"{type_info.typing if type_info else None}"
            )
        properties = {}
        required = []
        for item in get_fields(type_info.element):
            if item.metadata.get(fields.REQUIRED, False):
                required.append(item.name)
            json_property = self.field2json(item)
            if not json_property:
                continue
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
    ) -> Dict[str, str]:
        type_info = TypingInfo.get(schema)
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
            return {"oneOf": [self.get_schema_info(e) for e in type_info.element]}
        elif type_info.is_dataclass:
            name = self.add_schema_to_parse(type_info.element)
            return {"$ref": f"{SCHEMA_BASE_REF}{name}"}
        else:
            return self.get_primitive_info(type_info.element)

    def get_primitive_info(self, schema: type) -> Dict[str, str]:
        mapping = fields.PRIMITIVE_TYPES.get(schema)
        if not mapping:
            if is_subclass(schema, Enum):
                return {"type": "string", "enum": [e.name for e in schema]}
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


class OpenApiSpec(SchemaParser):
    """Open API document builder
    """

    def __init__(
        self,
        info: Optional[OpenApi] = None,
        default_content_type: str = "",
        default_responses: Optional[Dict] = None,
        allowed_tags: Iterable = None,
        validate_docs: bool = False,
        servers: Optional[List] = None,
        security: Optional[Dict[str, Dict]] = None,
    ) -> None:
        super().__init__(validate_docs=validate_docs)
        self.parameters: Dict = {}
        self.responses: Dict = {}
        self.tags: Dict = {}
        self.plugins: Dict = {}
        self.servers: List = servers or []
        self.default_content_type = default_content_type or "application/json"
        self.default_responses = default_responses or {}
        self.security = security
        self.doc = dict(
            openapi=OPENAPI, info=asdict(info or OpenApi()), paths=OrderedDict()
        )
        self.allowed_tags = allowed_tags

    @property
    def paths(self) -> Dict[str, Dict]:
        return self.doc["paths"]

    @property
    def title(self) -> str:
        return self.doc["info"]["title"]

    @property
    def version(self) -> str:
        return self.doc["info"]["version"]

    def build(
        self, app: web.Application, public: bool = True, private: bool = False
    ) -> Dict[str, JSONType]:
        """Build the ``doc`` dictionary by adding paths
        """
        self.logger = app.logger
        # Add errors schemas
        self.add_schema_to_parse(ValidationErrors)
        self.add_schema_to_parse(ErrorMessage)
        self.add_schema_to_parse(FieldError)
        security = self.security or {}
        self.doc["security"] = [
            {name: value.pop("scopes", [])} for name, value in security.items()
        ]
        # Build paths
        self._build_paths(app, public, private)
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
                servers=self.servers,
            )
        )
        return doc

    def routes(self, app: web.Application) -> List:
        return app.router.routes()

    # Internals

    def _build_paths(self, app: web.Application, public: bool, private: bool) -> None:
        """Loop through app paths and add
        schemas, parameters and paths objects to the spec
        """
        paths = self.paths
        base_path = app["cli"].base_path
        for route in self.routes(app):
            route_info = route.get_info()
            path = route_info.get("path", route_info.get("formatter", None))
            handler = route.handler
            include = is_subclass(handler, ApiPath) and self._include(
                handler.private, public, private
            )
            if include:
                N = len(base_path)
                path = path[N:]
                paths[path] = self._build_path_object(
                    path, handler, app, public, private
                )

        if self.validate_docs:
            self._validate_tags()

    def _validate_tags(self) -> None:
        for tag_name, tag_obj in self.tags.items():
            if self.allowed_tags and tag_name not in self.allowed_tags:
                raise InvalidSpecException(f'Tag "{tag_name}" not allowed')
            if "description" not in tag_obj:
                raise InvalidSpecException(f'Missing tag "{tag_name}" description')

    def _build_path_object(self, path: str, handler, path_obj, public, private):
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
                if not self._include(
                    method_doc.pop("private", private), public, private
                ):
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
                responses[response] = {
                    "description": data.get("description", ""),
                    "content": {"application/json": {"schema": rschema}},
                }
            doc["responses"] = responses

    def _get_request_body_object(
        self, type_info: Optional[TypingInfo], doc: Dict[str, str]
    ) -> None:
        if type_info:
            schema = self.get_schema_info(type_info)
            doc["requestBody"] = {"content": {"application/json": {"schema": schema}}}

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

    def _include(self, is_private, public, private):
        return (is_private and private) or (not is_private and public)


class SpecDoc:
    _spec_doc = None

    def get(self, request) -> Dict:
        if not self._spec_doc:
            app = request.app
            doc = app["spec"].build(app)
            if not doc.get("servers"):
                # build the server info
                doc["servers"] = [default_server(request)]
            self._spec_doc = doc
        return self._spec_doc


async def spec_root(request: web.Request) -> web.Response:
    """Return the OpenApi spec
    """
    return web.json_response(get_spec(request))
