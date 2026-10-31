"""Validation utilities for user input and data models."""
from datetime import datetime
from typing import List, Union
from budget_app.exceptions import ValidationError
from budget_app.models import TransactionType


def validate_date(date_str: str) -> str:
    """Validate date string with format YYYY-MM-DD."""
    if not isinstance(date_str, str):
        raise ValidationError("날짜 형식이 올바르지 않습니다 (YYYY-MM-DD).", hint="예: 2024-01-15")
    
    clean_date = date_str.strip()
    try:
        dt = datetime.strptime(clean_date, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        raise ValidationError(
            f"날짜 형식이 올바르지 않거나 존재하지 않는 날짜입니다: '{clean_date}'",
            hint="YYYY-MM-DD 형식으로 입력하세요. (예: 2024-01-15)"
        )


def validate_month(month_str: str) -> str:
    """Validate month string with format YYYY-MM."""
    if not isinstance(month_str, str):
        raise ValidationError("월 형식이 올바르지 않습니다 (YYYY-MM).", hint="예: 2024-01")

    clean_month = month_str.strip()
    try:
        dt = datetime.strptime(clean_month, "%Y-%m")
        return dt.strftime("%Y-%m")
    except ValueError:
        raise ValidationError(
            f"월 형식이 올바르지 않거나 존재하지 않는 월입니다: '{clean_month}'",
            hint="YYYY-MM 형식으로 입력하세요. (예: 2024-01)"
        )


def validate_type(type_str: str) -> str:
    """Validate transaction type ('income' or 'expense')."""
    if not isinstance(type_str, str):
        raise ValidationError("거래 타입은 'income' 또는 'expense'여야 합니다.", hint="income 또는 expense 중 하나를 입력하세요.")
    
    clean_type = type_str.strip().lower()
    valid_types = [t.value for t in TransactionType]
    if clean_type not in valid_types:
        raise ValidationError(
            f"허용되지 않은 거래 타입입니다: '{clean_type}'",
            hint="수입은 'income', 지출은 'expense'를 입력하세요."
        )
    return clean_type


def validate_amount(amount_val: Union[int, str]) -> int:
    """Validate transaction amount as a positive integer (> 0)."""
    try:
        if isinstance(amount_val, str):
            clean_str = amount_val.strip().replace(",", "")
            amount = int(clean_str)
        else:
            amount = int(amount_val)
    except (ValueError, TypeError):
        raise ValidationError(
            f"금액은 숫자(정수)여야 합니다: '{amount_val}'",
            hint="양수 정수 금액을 입력하세요. (예: 15000)"
        )

    if amount <= 0:
        raise ValidationError(
            f"금액은 0보다 큰 양수 정수여야 합니다: {amount}",
            hint="1원 이상의 금액을 입력하세요."
        )
    return amount


def validate_category_name(category_name: str) -> str:
    """Validate category name."""
    if not isinstance(category_name, str):
        raise ValidationError("카테고리명은 문자열이어야 합니다.", hint="카테고리명을 입력하세요.")
    
    clean_name = category_name.strip()
    if not clean_name:
        raise ValidationError("카테고리명은 비워둘 수 없습니다.", hint="공백이 아닌 카테고리명을 입력하세요. (예: food)")
    
    if "," in clean_name or "\n" in clean_name:
        raise ValidationError("카테고리명에는 쉼표(,)나 줄바꿈을 포함할 수 없습니다.", hint="특수문자를 제외한 이름을 입력하세요.")
    return clean_name


def parse_tags(tags_input: Union[str, List[str], None]) -> List[str]:
    """Parse and clean tags."""
    if not tags_input:
        return []
    if isinstance(tags_input, list):
        return [str(tag).strip() for tag in tags_input if str(tag).strip()]
    if isinstance(tags_input, str):
        return [tag.strip() for tag in tags_input.split(",") if tag.strip()]
    return []

