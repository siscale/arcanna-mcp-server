class ToolExceptionResponse:
    def __init__(self, status_code, error_message):
        self.status_code = status_code
        self.error_message = error_message

    def to_dict(self):
        return {
            "status_code": self.status_code,
            "error_message": self.error_message
        }
