"""Decorators for cross-cutting concerns (exception handling, logging, execution timing)."""
import functools
import sys
import time
from typing import Callable, Any
from budget_app.exceptions import BudgetAppError


def handle_cli_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to catch exceptions in CLI execution and output user-friendly error messages."""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            sys.stderr.write("\n[알림] 사용자에 의해 작업이 취소되었습니다.\n")
            sys.exit(130)
        except BudgetAppError as e:
            sys.stderr.write(f"{e}\n")
            sys.exit(1)
        except Exception as e:
            sys.stderr.write(f"[오류] 예기치 못한 시스템 오류가 발생했습니다: {e}\n")
            sys.stderr.write("[힌트] 입력값 및 저장소 파일 상태를 확인하거나 관리자에게 문의하세요.\n")
            sys.exit(1)
    return wrapper


def timed_execution(action_name: str = "") -> Callable[..., Any]:
    """Decorator to measure and optionally log execution time."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                elapsed = time.perf_counter() - start_time
                # Can be used for debug logging or performance metrics if needed
                # sys.stderr.write(f"[DEBUG] {action_name or func.__name__} took {elapsed:.4f}s\n")
        return wrapper
    return decorator


def log_action(action_name: str) -> Callable[..., Any]:
    """Decorator to log high-level business actions if debug/verbose is enabled."""
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)
        return wrapper
    return decorator

