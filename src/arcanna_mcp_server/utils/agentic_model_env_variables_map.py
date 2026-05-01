import os
from typing import List, Optional

from arcanna_mcp_server.models.agentic.env_variable import EnvVariable

agentic_model_env_variables_map = {
    "bedrock": {
        "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
        "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "AWS_REGION_NAME": os.getenv("AWS_REGION_NAME", "us-east-1")
    },
    "openai": {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "OPENAI_API_BASE": os.getenv("OPENAI_API_BASE"),
    },
    "anthropic": {
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY")
    },
    "vllm": {
        "HOSTED_VLLM_API_KEY": os.getenv("VLLM_API_KEY"),
        "HOSTED_VLLM_API_BASE": os.getenv("VLLM_API_BASE"),
    }
}


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
