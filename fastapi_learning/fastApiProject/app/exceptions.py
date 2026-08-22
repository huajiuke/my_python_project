"""业务异常定义。"""


class BusinessError(Exception):
    """业务异常：status_code 对应 HTTP 状态码，message 是用户可见信息。"""

    def __init__(
        self,
        message: str,
        status_code: int = 400,
        code: str = "BUSINESS_ERROR",
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code
