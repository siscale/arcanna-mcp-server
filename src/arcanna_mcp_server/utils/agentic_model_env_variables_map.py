import os
from typing import List, Optional

from arcanna_mcp_server.models.agentic.env_variable import EnvVariable


def parse_env_variables_request(env_variables: Optional[List[EnvVariable]]):
    if env_variables is None:
        return None
    env_variables_payload = []
    for env_var in env_variables:
        if os.getenv(env_var.name) is None:
            continue
        env_variables_payload.append({
            "name": env_var.name,
            "value": os.getenv(env_var.name),
            "is_secret": env_var.is_secret,
            "should_encrypt": True
        })
    return env_variables_payload
