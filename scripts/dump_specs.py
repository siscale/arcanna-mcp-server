"""Dump exposer and agents_exposer OpenAPI specs, annotated with each operation's API key scopes.

Run from a modular-framework checkout, with its venv (agents_exposer needs env_exp):
    cd ~/CODE/siscale/modular-framework2
    venv/bin/python ~/CODE/siscale/arcanna-mcp-server/scripts/dump_specs.py exposer
    env_exp/bin/python ~/CODE/siscale/arcanna-mcp-server/scripts/dump_specs.py agents
"""
import json
import os
import sys

from fastapi import FastAPI
from fastapi.routing import APIRoute

sys.path.insert(0, os.getcwd())

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "specs")


def _scopes(dependant) -> list:
    found = []
    for dependency in dependant.dependencies:
        scopes = getattr(dependency.call, "scopes", None)
        if scopes:
            found.extend(getattr(scope, "value", scope) for scope in scopes)
        found.extend(_scopes(dependency))
    return sorted(set(found))


def _build(which: str) -> FastAPI:
    from webservices.exposer.api.openapi_ids import arcanna_operation_id
    app = FastAPI(generate_unique_id_function=arcanna_operation_id)
    if which == "exposer":
        from webservices.exposer.api.v1.api import api_router as v1
        from webservices.exposer.api.v2.api import api_router as v2
        app.include_router(v1, prefix="/api/v1")
        app.include_router(v2, prefix="/api/v2")
    else:
        from webservices.agents_exposer.api.v1.api import api_router
        app.include_router(api_router, prefix="/api/v1")
    return app


def main(which: str) -> None:
    app = _build(which)
    spec = app.openapi()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        for method in route.methods:
            operation = spec["paths"].get(route.path_format, {}).get(method.lower())
            if operation is not None:
                operation["x-arcanna-scopes"] = _scopes(route.dependant)
    with open(os.path.join(OUT_DIR, f"{which}.json"), "w") as out:
        json.dump(spec, out, indent=1, sort_keys=True)


if __name__ == "__main__":
    main(sys.argv[1])
