"""Generate MCP tool stubs from the dumped Arcanna OpenAPI specs.

Reads scripts/specs/{exposer,agents}.json (see dump_specs.py) and scripts/tool_map.py, and appends a stub for
every mapped tool that its target module does not define yet. Existing (hand edited) tools are never touched.
The output is a starting point: trim docstrings to the tool template and simplify awkward bodies by hand.

    python scripts/gen_tools.py            # write missing stubs
    python scripts/gen_tools.py --check    # list mapped tools that are missing, exit 1 if any
"""
import json
import keyword
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from tool_map import TOOLS  # noqa: E402

PACKAGE_DIR = os.path.join(ROOT, "src", "arcanna_mcp_server")
JSON_TYPES = {"string": "str", "integer": "int", "number": "float", "boolean": "bool", "object": "dict"}


def load_specs():
    specs = {}
    for service in ("exposer", "agents"):
        with open(os.path.join(ROOT, "scripts", "specs", f"{service}.json")) as spec_file:
            specs[service] = json.load(spec_file)
    return specs


def find_operation(spec, operation_id):
    for path, operations in spec["paths"].items():
        for method, operation in operations.items():
            if operation.get("operationId") == operation_id:
                return method, path, operation
    raise KeyError(operation_id)


def resolve(spec, schema):
    while "$ref" in schema:
        schema = spec["components"]["schemas"][schema["$ref"].split("/")[-1]]
    return schema


def python_type(spec, schema) -> str:
    if "$ref" in schema:
        target = resolve(spec, schema)
        if "enum" in target:
            return "Literal[" + ", ".join(repr(value) for value in target["enum"]) + "]"
        return python_type(spec, target) if target.get("type") != "object" else "dict"
    if "enum" in schema:
        return "Literal[" + ", ".join(repr(value) for value in schema["enum"]) + "]"
    for union_key in ("anyOf", "oneOf"):
        if union_key in schema:
            members = [member for member in schema[union_key] if member.get("type") != "null"]
            optional = len(members) != len(schema[union_key])
            inner = python_type(spec, members[0]) if len(members) == 1 else \
                "Union[" + ", ".join(python_type(spec, member) for member in members) + "]"
            return f"Optional[{inner}]" if optional else inner
    if schema.get("type") == "array":
        return f"List[{python_type(spec, schema.get('items', {}))}]"
    return JSON_TYPES.get(schema.get("type"), "Any")


def python_name(name: str) -> str:
    cleaned = re.sub(r"\W", "_", name)
    return cleaned + "_" if keyword.iskeyword(cleaned) else cleaned


def one_line(text: str) -> str:
    return " ".join((text or "").split())


class Argument:
    def __init__(self, name, type_, description, required, default, location):
        self.wire_name = name
        self.name = python_name(name)
        self.type_ = type_
        self.description = one_line(description) or name
        self.required = required
        self.default = default
        self.location = location

    def render(self) -> str:
        type_ = self.type_
        if not self.required and not type_.startswith("Optional["):
            type_ = f"Optional[{type_}]"
        annotated = f"Annotated[{type_}, Field(description={self.description!r})]"
        if self.required:
            return f"        {self.name}: {annotated},"
        return f"        {self.name}: {annotated} = {self.default!r},"


def collect_arguments(spec, operation):
    arguments = []
    for param in operation.get("parameters", []):
        if param["in"] == "header":
            continue
        schema = param.get("schema", {})
        arguments.append(Argument(param["name"], python_type(spec, schema),
                                  param.get("description") or schema.get("description"),
                                  param.get("required", False), schema.get("default"), param["in"]))
    content = operation.get("requestBody", {}).get("content", {})
    body_schema = (content.get("application/json") or content.get("multipart/form-data") or {}).get("schema")
    if body_schema:
        body = resolve(spec, body_schema)
        required = set(body.get("required", []))
        for name, field in body.get("properties", {}).items():
            location = "form" if "multipart/form-data" in content else "body"
            arguments.append(Argument(name, python_type(spec, field), field.get("description"), name in required,
                                      field.get("default"), location))
    arguments.sort(key=lambda argument: not argument.required)
    return arguments


def render_tool(tool_name, entry, spec):
    method, path, operation = find_operation(spec, entry["op"])
    arguments = collect_arguments(spec, operation)
    scopes = entry.get("scopes") or operation.get("x-arcanna-scopes") or ["public"]
    doc = one_line(operation.get("summary")) + "\n\n    " + one_line(operation.get("description"))
    path_expr = re.sub(r"{(\w+)}", lambda m: "{" + python_name(m.group(1)) + "}", path)

    def mapping(location):
        items = [f'"{a.wire_name}": {a.name}' for a in arguments if a.location == location]
        return "{" + ", ".join(items) + "}" if items else None

    call_args = [repr(method.upper()), f'f"{path_expr}"']
    if entry["service"] != "exposer":
        call_args.append("service=AGENTS")
    for location, keyword_name in (("query", "params"), ("body", "json"), ("form", "data")):
        rendered = mapping(location)
        if rendered:
            call_args.append(f"{keyword_name}={rendered}")

    lines = ["", "", "@handle_exceptions", f"@requires_scope({', '.join(repr(s) for s in scopes)})",
             f"async def {tool_name}("]
    lines += [argument.render() for argument in arguments]
    lines += [") -> Any:", f'    """{doc.strip()}"""', f"    return await call({', '.join(call_args)})", ""]
    return "\n".join(lines)


def module_path(entry):
    return os.path.join(PACKAGE_DIR, entry["server"], "tools", f"{entry['module']}.py")


def defined(path, tool_name):
    if not os.path.exists(path):
        return False
    with open(path) as module_file:
        return re.search(rf"^async def {tool_name}\(", module_file.read(), re.M) is not None


HEADER = '''from typing import Annotated, Any, Callable, Dict, List, Literal, Optional, Union

from pydantic import Field

from arcanna_mcp_server.common.errors import handle_exceptions
from arcanna_mcp_server.common.http import AGENTS, call
from arcanna_mcp_server.common.scopes import requires_scope


def export_tools() -> List[Callable]:
    return []
'''


def main(check_only: bool):
    specs = load_specs()
    missing = [(name, entry) for name, entry in TOOLS.items() if not defined(module_path(entry), name)]
    if check_only:
        for name, entry in missing:
            print(f"missing: {entry['server']}/{entry['module']}.{name}")
        sys.exit(1 if missing else 0)

    for name, entry in missing:
        path = module_path(entry)
        if not os.path.exists(path):
            with open(path, "w") as module_file:
                module_file.write(HEADER)
        with open(path, "a") as module_file:
            module_file.write(render_tool(name, entry, specs[entry["service"]]))
        print(f"generated {entry['server']}/{entry['module']}.{name} (add it to export_tools)")


if __name__ == "__main__":
    main("--check" in sys.argv)
