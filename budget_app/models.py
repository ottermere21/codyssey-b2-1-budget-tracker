"""Data models for Budget App."""
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Any, Optional


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


@dataclass
class Transaction:
    """Represents a single income or expense transaction."""
    id: str
    date: str  # YYYY-MM-DD
    type: str  # income or expense
    amount: int  # Positive integer
    category: str
    memo: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert transaction to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transaction":
        """Create transaction from dictionary."""
        tags = data.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        return cls(
            id=str(data["id"]),
            date=str(data["date"]),
            type=str(data["type"]),
            amount=int(data["amount"]),
            category=str(data["category"]),
            memo=str(data.get("memo", "")),
            tags=tags,
        )


@dataclass
class Category:
    """Represents a budget category."""
    name: str

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Category":
        return cls(name=str(data["name"]))


@dataclass
class Budget:
    """Represents a monthly budget."""
    month: str  # YYYY-MM
    amount: int

    def to_dict(self) -> Dict[str, Any]:
        return {"month": self.month, "amount": self.amount}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Budget":
        return cls(month=str(data["month"]), amount=int(data["amount"]))


@dataclass
class SummaryResult:
    """Represents a monthly summary result."""
    month: str
    total_income: int
    total_expense: int
    balance: int
    category_expenses: List[tuple[str, int]]  # Sorted list of (category, total_amount)
    budget_amount: Optional[int] = None
    has_data: bool = True

    @property
    def usage_rate(self) -> Optional[float]:
        """Calculate budget usage rate in percentage."""
        if self.budget_amount and self.budget_amount > 0:
            return round((self.total_expense / self.budget_amount) * 100, 1)
        return None

    @property
    def is_over_budget(self) -> bool:
        """Check if monthly expenses exceeded the budget."""
        if self.budget_amount is not None:
            return self.total_expense > self.budget_amount
        return False

