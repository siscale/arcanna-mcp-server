import functools


class ArcannaApiError(Exception):
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class ToolExceptionResponse:
    def __init__(self, status_code, error_message):
        self.status_code = status_code
        self.error_message = error_message

    def to_dict(self):
        return {
            "status_code": self.status_code,
            "error_message": self.error_message
        }


def handle_exceptions(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ArcannaApiError as e:
            return ToolExceptionResponse(status_code=e.status_code, error_message=e.message).to_dict()
        except ValueError as e:
            return ToolExceptionResponse(status_code=400, error_message=str(e)).to_dict()
        except Exception as e:
            return ToolExceptionResponse(status_code=500, error_message=str(e)).to_dict()
    return wrapper
