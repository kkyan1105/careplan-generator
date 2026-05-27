from django.http import JsonResponse
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response


class BaseAppException(Exception):
    http_status = 500
    error_type = "server_error"

    def __init__(self, message, code=None, detail=None):
        self.message = message
        self.code = code or self.__class__.__name__
        self.detail = detail
        super().__init__(message)

    def to_dict(self):
        return {
            "type": self.error_type,
            "code": self.code,
            "message": self.message,
            "detail": self.detail,
        }


class ValidationError(BaseAppException):
    http_status = 400
    error_type = "validation_error"


class BlockError(BaseAppException):
    http_status = 409
    error_type = "block_error"


class WarningException(BaseAppException):
    http_status = 200
    error_type = "warning"


# ── DRF exception handler ────────────────────────────────────────────────────
# Registered in settings.REST_FRAMEWORK['EXCEPTION_HANDLER'].
# Handles BaseAppException and DRF's own ValidationError in DRF views.

def drf_exception_handler(exc, context):
    if isinstance(exc, BaseAppException):
        return Response(exc.to_dict(), status=exc.http_status)

    if isinstance(exc, DRFValidationError):
        return Response(
            {
                "type": "validation_error",
                "code": "VALIDATION_FAILED",
                "message": "Input validation failed.",
                "detail": exc.detail,
            },
            status=400,
        )

    return None  # let DRF fall back to its default 500 handling


# ── Django middleware ─────────────────────────────────────────────────────────
# Added to settings.MIDDLEWARE.
# Handles BaseAppException for plain Django views (non-DRF).

class AppExceptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, BaseAppException):
            return JsonResponse(exception.to_dict(), status=exception.http_status)
        return None
