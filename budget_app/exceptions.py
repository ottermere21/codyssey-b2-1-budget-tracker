"""Custom exceptions for Budget App."""
from typing import Optional


class BudgetAppError(Exception):
    """Base exception for budget app errors with human-friendly message and hint."""

    def __init__(self, message: str, hint: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.hint = hint

    def __str__(self) -> str:
        if self.hint:
            return f"[오류] {self.message}\n[힌트] {self.hint}"
        return f"[오류] {self.message}"


class ValidationError(BudgetAppError):
    """Raised when user input or data validation fails."""
    pass


class NotFoundError(BudgetAppError):
    """Raised when an entity (transaction, category, etc.) is not found."""
    pass


class DuplicateError(BudgetAppError):
    """Raised when attempting to create a duplicate entity."""
    pass


class CategoryInUseError(BudgetAppError):
    """Raised when attempting to delete a category that is still referenced by transactions."""
    pass


class BudgetAppIOError(BudgetAppError):
    """Raised when file reading, writing, or path access fails."""
    pass

