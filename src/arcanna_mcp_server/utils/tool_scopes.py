import requests
from typing import List
from arcanna_mcp_server.constants import GET_TOKEN_SCOPE_URL
from arcanna_mcp_server.environment import MANAGEMENT_API_KEY


def requires_scope(*scope):
    def decorator(func):
        func.required_scope = scope
        return func
    return decorator


def get_api_key_scope() -> List[str]:
    headers = {
        "x-arcanna-api-key": MANAGEMENT_API_KEY
    }
    response = requests.get(
        GET_TOKEN_SCOPE_URL,
        headers=headers
    )
    json_response = response.json()

    if response.status_code != 200 or not isinstance(json_response, list):
        raise Exception(f"Failed to get API key scope. Status code: {response.status_code}. Response: {response}")

    return json_response


def filter_by_scope(callables_list, api_key_scope):
    filtered_callables_list = []
    for func in callables_list:
        if not hasattr(func, 'required_scopes'):
            print(f"Function {func.__name__} does not have required_scopes attribute.")
            continue

        if not set(func.required_permission).issubset(api_key_scope):
            print(f"Function {func.__name__} requires scopes {func.required_permission}"
                  f" which is not in api key scopes={api_key_scope}.")
            continue

        filtered_callables_list.append(func)

    return filtered_callables_list
