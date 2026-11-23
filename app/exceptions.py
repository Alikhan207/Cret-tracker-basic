"""Custom exception hierarchy.

Services raise these; the web layer and the API layer translate them into
flash messages / HTML pages / JSON responses with the right HTTP status code.
Keeping them separate from Flask means the business logic can be tested
without a web server.
"""


class AppError(Exception):
    """Base class for every expected (handled) error in the application."""

    status_code = 400

    def __init__(self, message: str = "Something went wrong"):
        super().__init__(message)
        self.message = message


class ValidationError(AppError):
    """Input failed validation. `errors` maps field name -> message."""

    status_code = 400

    def __init__(self, errors: dict[str, str]):
        super().__init__("Please fix the highlighted fields")
        self.errors = errors


class AuthenticationError(AppError):
    status_code = 401


class PermissionDenied(AppError):
    status_code = 403


class NotFoundError(AppError):
    status_code = 404


class DuplicateError(AppError):
    status_code = 409
