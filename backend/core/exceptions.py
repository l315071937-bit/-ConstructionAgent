class AppError(Exception):
    def __init__(self, code: str, message: str, http_status: int = 400):
        self.code = code
        self.message = message
        self.http_status = http_status
        super().__init__(message)


class AuthError(AppError):
    def __init__(self, code="AUTH_TOKEN_INVALID", message="认证失败"):
        super().__init__(code, message, 401)


class PermissionError_(AppError):
    def __init__(self, message="无权限访问该项目"):
        super().__init__("PERMISSION_DENIED", message, 403)


class NotFoundError(AppError):
    def __init__(self, code: str, message: str):
        super().__init__(code, message, 404)
