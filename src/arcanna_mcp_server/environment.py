import os


MANAGEMENT_API_KEY = os.getenv("ARCANNA_MANAGEMENT_API_KEY")
# TODO: Remove
INPUT_API_KEY = "QiNMkXiTf3cjffuh_1i8Km_8kddfLuHzq_N5XwCGUNmSoYk6uZN3HAH6PEd3BUkKEaDTs-EQQmLWzoyf6e85iw"
ARCANNA_HOST = os.getenv("ARCANNA_HOST", "")
TRANSPORT_MODE = os.getenv("TRANSPORT_MODE", "stdio")


def validate_environment_variables():
    if MANAGEMENT_API_KEY is None:
        raise Exception("Arcanna management api key not found")

    if ARCANNA_HOST is None:
        raise Exception("Arcanna HOST not found.")

    if TRANSPORT_MODE not in ["stdio", "sse"]:
        raise Exception(f"TRANSPORT_MODE {TRANSPORT_MODE} not supported.")
