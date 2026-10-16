import logging

import requests

from arcanna_mcp_server.common.http import EXPOSER, base_url, headers

logger = logging.getLogger(__name__)

PUBLIC = "public"


def requires_scope(*scope):
    def decorator(func):
        func.required_scope = scope
        return func
    return decorator


def get_base_scope(scope_string: str):
    """action:resource_category:resource_type:resource_id -> action:resource_category"""
    return ':'.join(scope_string.split(':')[:2])


SCOPES_TIMEOUT_SECONDS = 15


def get_api_key_scope() -> set:
    url = base_url(EXPOSER) + "/api/v2/token/scopes"
    try:
        response = requests.get(url, headers=headers(), timeout=SCOPES_TIMEOUT_SECONDS)
    except requests.RequestException as e:
        raise Exception(f"Cannot reach Arcanna at {url} to read the API key scopes: {e}") from e
    json_response = response.json()

    if response.status_code != 200 or not isinstance(json_response, list):
        raise Exception(f"Failed to get API key scope."
                        f" Status code: {response.status_code}."
                        f" Response: {response}")

    return {get_base_scope(scope) for scope in json_response}


def filter_by_scope(callables_list, api_key_scope: set):
    filtered_callables_list = []
    for func in callables_list:
        if not hasattr(func, 'required_scope'):
            logger.warning(f"Function {func.__name__} does not have required_scope attribute.")
            continue

        if func.required_scope[0] == PUBLIC or set(func.required_scope).issubset(api_key_scope):
            filtered_callables_list.append(func)
        else:
            logger.warning(f"Function {func.__name__} requires scope {func.required_scope}")

    return filtered_callables_list
