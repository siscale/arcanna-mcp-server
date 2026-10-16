import os
import re

MANAGEMENT_API_KEY = os.getenv("ARCANNA_MANAGEMENT_API_KEY")
ARCANNA_HOST = os.getenv("ARCANNA_HOST")
ARCANNA_AGENTS_HOST = os.getenv("ARCANNA_AGENTS_HOST")
TRANSPORT_MODE = os.getenv("TRANSPORT_MODE", "stdio")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("ARCANNA_REQUEST_TIMEOUT_SECONDS", "300"))

ARCANNA_AGENTS_DEFAULT_PORT = "9888"

if ARCANNA_AGENTS_HOST is None and ARCANNA_HOST:
    base_url = re.match(r'https?://[^:/]+', ARCANNA_HOST)
    if base_url:
        ARCANNA_AGENTS_HOST = base_url.group() + ":" + ARCANNA_AGENTS_DEFAULT_PORT


def validate_environment_variables():
    if MANAGEMENT_API_KEY is None:
        raise Exception("ARCANNA_MANAGEMENT_API_KEY env variable not found.")

    if ARCANNA_HOST is None:
        raise Exception("ARCANNA_HOST env variable not found.")

    if ARCANNA_AGENTS_HOST is None:
        raise Exception("ARCANNA_AGENTS_HOST env variable not found.")

    if TRANSPORT_MODE not in ["stdio", "sse"]:
        raise Exception(f"TRANSPORT_MODE {TRANSPORT_MODE} not supported.")
