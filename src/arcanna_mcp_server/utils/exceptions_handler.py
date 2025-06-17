import functools

from arcanna_mcp_server.utils.tool_exception_response import ToolExceptionResponse


def handle_exceptions(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ValueError:
            return ToolExceptionResponse(status_code=500, error_message="ValueError. MCP server internal error").to_dict()
        except Exception as e:
            return ToolExceptionResponse(status_code=500, error_message=str(e)).to_dict()
    return wrapper
