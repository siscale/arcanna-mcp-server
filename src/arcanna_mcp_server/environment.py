import os
import re

MANAGEMENT_API_KEY = os.getenv("ARCANNA_MANAGEMENT_API_KEY")
ARCANNA_HOST = os.getenv("ARCANNA_HOST")
ARCANNA_EXPOSER_HOST = ARCANNA_HOST
ARCANNA_AGENTS_HOST = os.getenv("ARCANNA_AGENTS_HOST")
ARCANNA_RAG_HOST = os.getenv("ARCANNA_RAG_HOST")
TRANSPORT_MODE = os.getenv("TRANSPORT_MODE", "stdio")

ARCANNA_EXPOSER_DEFAULT_PORT = "9666"
ARCANNA_AGENTS_DEFAULT_PORT = "9888"
ARCANNA_RAG_DEFAULT_PORT = "5356"

if ARCANNA_AGENTS_HOST is None:
    base_url = re.match(r'https?://[^:]+', ARCANNA_HOST).group()
    ARCANNA_AGENTS_HOST = base_url + ":" + ARCANNA_AGENTS_DEFAULT_PORT

if ARCANNA_RAG_HOST is None:
    base_url = re.match(r'https?://[^:]+', ARCANNA_HOST).group()
    ARCANNA_RAG_HOST = base_url + ":" + ARCANNA_RAG_DEFAULT_PORT


def validate_environment_variables():
    if MANAGEMENT_API_KEY is None:
        raise Exception("ARCANNA_MANAGEMENT_API_KEY env variable not found")

    if ARCANNA_HOST is None:
        raise Exception("ARCANNA_HOST env variable not found.")

    if ARCANNA_AGENTS_HOST is None:
        raise Exception("ARCANNA_AGENTS_HOST env variable not found.")

    if ARCANNA_RAG_HOST is None:
        raise Exception("ARCANNA_AGENTS_HOST env variable not found.")

    if TRANSPORT_MODE not in ["stdio", "sse"]:
        raise Exception(f"TRANSPORT_MODE {TRANSPORT_MODE} not supported.")

