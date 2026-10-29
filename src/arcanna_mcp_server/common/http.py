import asyncio
from typing import Any, Optional

import requests

from arcanna_mcp_server.common import environment
from arcanna_mcp_server.common.errors import ArcannaApiError

EXPOSER = "exposer"
AGENTS = "agents"


def base_url(service: str) -> str:
    return (environment.ARCANNA_AGENTS_HOST if service == AGENTS else environment.ARCANNA_HOST) or ""


def headers(json_body: bool = True) -> dict:
    result = {"x-arcanna-api-key": environment.MANAGEMENT_API_KEY}
    if json_body:
        result["Content-Type"] = "application/json"
    return result


def drop_none(values: Optional[dict]) -> Optional[dict]:
    if values is None:
        return None
    return {key: value for key, value in values.items() if value is not None}


def _error_message(response: requests.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text or response.reason
    if isinstance(body, dict):
        for key in ("detail", "reason_details", "error_message", "reason", "message"):
            if body.get(key):
                return str(body[key])
    return str(body)


def _request(method: str, url: str, params: Optional[dict], json: Any, files: Any, data: Optional[dict]) -> Any:
    response = requests.request(method, url, headers=headers(json_body=files is None), params=params, json=json,
                                files=files, data=data, timeout=environment.REQUEST_TIMEOUT_SECONDS)
    if response.status_code >= 400:
        raise ArcannaApiError(response.status_code, _error_message(response))
    if not response.content:
        return {}
    try:
        return response.json()
    except ValueError:
        return {"content": response.text}


async def call(method: str, path: str, *, service: str = EXPOSER, params: Optional[dict] = None, json: Any = None,
               files: Any = None, data: Optional[dict] = None) -> Any:
    """Calls an Arcanna API; None-valued params and top-level body keys are dropped so server defaults apply."""
    body = drop_none(json) if isinstance(json, dict) else json
    return await asyncio.to_thread(_request, method.upper(), base_url(service) + path, drop_none(params), body,
                                   files, data)
