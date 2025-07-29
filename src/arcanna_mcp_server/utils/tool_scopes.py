import logging
import requests
from arcanna_mcp_server.constants import GET_TOKEN_SCOPE_URL
from arcanna_mcp_server.environment import MANAGEMENT_API_KEY


logger = logging.getLogger(__name__)


def requires_scope(*scope):
    def decorator(func):
        func.required_scope = scope
        return func
    return decorator


def get_base_scope(scope_string: str):
    """
    action:resource_category:resource_type:resource_id -> action:resource_category
    """
    return ':'.join(scope_string.split(':')[:2])


def get_api_key_scope() -> set:
    headers = {"x-arcanna-api-key": MANAGEMENT_API_KEY}
    response = requests.get(
        GET_TOKEN_SCOPE_URL,
        headers=headers
    )
    json_response = response.json()

    if response.status_code != 200 or not isinstance(json_response, list):
        raise Exception(f"Failed to get API key scope."
                        f" Status code: {response.status_code}."
                        f" Response: {response}")

    base_scopes = [get_base_scope(scope) for scope in json_response]
    return set(base_scopes)


def filter_by_scope(callables_list):
    filtered_callables_list = []
    api_key_scope = get_api_key_scope()

    for func in callables_list:
        if not hasattr(func, 'required_scope'):
            logger.warning(f"Function {func.__name__} does not have required_scope attribute.")
            continue

        if func.required_scope[0] == 'public':
            logger.warning(f"Function {func.__name__} have public scope.")
            filtered_callables_list.append(func)
            continue

        if not set(func.required_scope).issubset(api_key_scope):
            logger.warning(f"Function {func.__name__} requires scope {func.required_scope}")
            continue

        filtered_callables_list.append(func)

    return filtered_callables_list
