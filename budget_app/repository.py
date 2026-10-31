"""File-based repository layer supporting streaming processing with generators."""
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Generator, List, Optional, Dict, Any
from budget_app.exceptions import BudgetAppIOError
from budget_app.models import Transaction, Category, Budget


DEFAULT_CATEGORIES = ["food", "transport", "living", "leisure", "salary", "etc"]


def reverse_readline_generator(file_path: Path, buffer_size: int = 8192) -> Generator[str, None, None]:
    """Yield lines in reverse order (bottom-to-top) using chunk-based streaming without full memory loading."""
    if not file_path.exists() or file_path.stat().st_size == 0:
        return

    with open(file_path, "rb") as f:
        f.seek(0, os.SEEK_END)
        position = f.tell()
        buffer = b""

        while position > 0:
            read_size = min(buffer_size, position)
            position -= read_size
            f.seek(position)
            chunk = f.read(read_size)
            buffer = chunk + buffer
            lines = buffer.split(b"\n")

            # lines[0] may be partial line if we haven't reached the beginning of file
            if position > 0:
                buffer = lines[0]
                lines_to_yield = lines[1:]
            else:
                buffer = b""
                lines_to_yield = lines

            for line in reversed(lines_to_yield):
                decoded = line.decode("utf-8").strip()
                if decoded:
                    yield decoded

        if buffer:
            decoded = buffer.decode("utf-8").strip()
            if decoded:
                yield decoded


def forward_readline_generator(file_path: Path) -> Generator[str, None, None]:
    """Yield lines in forward order (top-to-bottom) using streaming."""
    if not file_path.exists():
        return

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()
            if stripped:
                yield stripped


class TransactionRepository:
    """Repository for Transaction persistence in JSONL format."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.file_path = self.data_dir / "transactions.jsonl"
        self._init_storage()

    def _init_storage(self) -> None:
        """Ensure data directory and transactions file exist."""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            if not self.file_path.exists():
                self.file_path.touch()
        except OSError as e:
            raise BudgetAppIOError(
                f"거래 내역 저장소 초기화 실패: {e}",
                hint=f"경로 접근 권한을 확인하세요: {self.data_dir}"
            )

    def get_next_id(self) -> str:
        """Generate the next transaction ID (e.g. TX-000001) by finding max existing ID."""
        max_num = 0
        id_pattern = re.compile(r"^TX-(\d+)$")

        # Use streaming to find max ID
        for tx in self.stream_all(reverse=False):
            match = id_pattern.match(tx.id)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num

        return f"TX-{max_num + 1:06d}"

    def add(self, tx: Transaction) -> None:
        """Append a transaction to JSONL file."""
        try:
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(tx.to_dict(), ensure_ascii=False) + "\n")
        except OSError as e:
            raise BudgetAppIOError(
                f"거래 내역 저장 실패: {e}",
                hint=f"저장 파일 권한 및 디스크 용량을 확인하세요: {self.file_path}"
            )

    def stream_all(self, reverse: bool = False) -> Generator[Transaction, None, None]:
        """Stream all transactions one by one as a generator."""
        line_gen = reverse_readline_generator(self.file_path) if reverse else forward_readline_generator(self.file_path)
        for line in line_gen:
            try:
                data = json.loads(line)
                yield Transaction.from_dict(data)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue

    def find_by_id(self, tx_id: str) -> Optional[Transaction]:
        """Find a transaction by ID using streaming."""
        for tx in self.stream_all(reverse=True):
            if tx.id == tx_id:
                return tx
        return None

    def update(self, updated_tx: Transaction) -> bool:
        """Update transaction atomically using a temporary file and replace."""
        found = False
        try:
            temp_file = tempfile.NamedTemporaryFile("w", dir=self.data_dir, delete=False, encoding="utf-8")
            temp_path = Path(temp_file.name)
            try:
                with temp_file:
                    for tx in self.stream_all(reverse=False):
                        if tx.id == updated_tx.id:
                            temp_file.write(json.dumps(updated_tx.to_dict(), ensure_ascii=False) + "\n")
                            found = True
                        else:
                            temp_file.write(json.dumps(tx.to_dict(), ensure_ascii=False) + "\n")
                if found:
                    os.replace(temp_path, self.file_path)
                else:
                    if temp_path.exists():
                        temp_path.unlink()
                return found
            except Exception:
                if temp_path.exists():
                    temp_path.unlink()
                raise
        except OSError as e:
            raise BudgetAppIOError(
                f"거래 내역 수정 중 파일 오류 발생: {e}",
                hint=f"저장소 파일 상태를 확인하세요: {self.file_path}"
            )

    def delete(self, tx_id: str) -> bool:
        """Delete transaction atomically using a temporary file and replace."""
        found = False
        try:
            temp_file = tempfile.NamedTemporaryFile("w", dir=self.data_dir, delete=False, encoding="utf-8")
            temp_path = Path(temp_file.name)
            try:
                with temp_file:
                    for tx in self.stream_all(reverse=False):
                        if tx.id == tx_id:
                            found = True
                        else:
                            temp_file.write(json.dumps(tx.to_dict(), ensure_ascii=False) + "\n")
                if found:
                    os.replace(temp_path, self.file_path)
                else:
                    if temp_path.exists():
                        temp_path.unlink()
                return found
            except Exception:
                if temp_path.exists():
                    temp_path.unlink()
                raise
        except OSError as e:
            raise BudgetAppIOError(
                f"거래 내역 삭제 중 파일 오류 발생: {e}",
                hint=f"저장소 파일 상태를 확인하세요: {self.file_path}"
            )


class CategoryRepository:
    """Repository for Category persistence in JSONL format."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.file_path = self.data_dir / "categories.jsonl"
        self._init_storage()

    def _init_storage(self) -> None:
        """Ensure data directory and categories file exist with default categories if empty."""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            if not self.file_path.exists() or self.file_path.stat().st_size == 0:
                with open(self.file_path, "w", encoding="utf-8") as f:
                    for cat in DEFAULT_CATEGORIES:
                        f.write(json.dumps({"name": cat}, ensure_ascii=False) + "\n")
        except OSError as e:
            raise BudgetAppIOError(
                f"카테고리 저장소 초기화 실패: {e}",
                hint=f"경로 접근 권한을 확인하세요: {self.data_dir}"
            )

    def get_all(self) -> List[str]:
        """Return all category names."""
        categories: List[str] = []
        for line in forward_readline_generator(self.file_path):
            try:
                data = json.loads(line)
                name = str(data.get("name", "")).strip()
                if name and name not in categories:
                    categories.append(name)
            except json.JSONDecodeError:
                continue
        return categories

    def exists(self, category_name: str) -> bool:
        """Check if category exists."""
        clean_name = category_name.strip().lower()
        return any(c.lower() == clean_name for c in self.get_all())

    def add(self, category_name: str) -> None:
        """Add new category."""
        clean_name = category_name.strip()
        try:
            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"name": clean_name}, ensure_ascii=False) + "\n")
        except OSError as e:
            raise BudgetAppIOError(
                f"카테고리 저장 실패: {e}",
                hint=f"저장 파일 권한을 확인하세요: {self.file_path}"
            )

    def remove(self, category_name: str) -> bool:
        """Remove a category atomically."""
        clean_name = category_name.strip().lower()
        found = False
        all_categories = self.get_all()
        new_categories = []
        for cat in all_categories:
            if cat.lower() == clean_name:
                found = True
            else:
                new_categories.append(cat)

        if not found:
            return False

        try:
            temp_file = tempfile.NamedTemporaryFile("w", dir=self.data_dir, delete=False, encoding="utf-8")
            temp_path = Path(temp_file.name)
            try:
                with temp_file:
                    for cat in new_categories:
                        temp_file.write(json.dumps({"name": cat}, ensure_ascii=False) + "\n")
                os.replace(temp_path, self.file_path)
                return True
            except Exception:
                if temp_path.exists():
                    temp_path.unlink()
                raise
        except OSError as e:
            raise BudgetAppIOError(
                f"카테고리 삭제 중 파일 오류 발생: {e}",
                hint=f"저장소 파일 상태를 확인하세요: {self.file_path}"
            )


class BudgetRepository:
    """Repository for Budget persistence in JSONL format."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.file_path = self.data_dir / "budgets.jsonl"
        self._init_storage()

    def _init_storage(self) -> None:
        """Ensure data directory and budgets file exist."""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            if not self.file_path.exists():
                self.file_path.touch()
        except OSError as e:
            raise BudgetAppIOError(
                f"예산 저장소 초기화 실패: {e}",
                hint=f"경로 접근 권한을 확인하세요: {self.data_dir}"
            )

    def get_all(self) -> Dict[str, int]:
        """Return all budgets mapped by month (YYYY-MM)."""
        budgets: Dict[str, int] = {}
        for line in forward_readline_generator(self.file_path):
            try:
                data = json.loads(line)
                month = str(data.get("month", "")).strip()
                amount = int(data.get("amount", 0))
                if month:
                    budgets[month] = amount
            except (json.JSONDecodeError, ValueError):
                continue
        return budgets

    def get_budget(self, month: str) -> Optional[int]:
        """Get budget for a specific month."""
        clean_month = month.strip()
        budgets = self.get_all()
        return budgets.get(clean_month)

    def set_budget(self, month: str, amount: int) -> None:
        """Set or update budget for a month atomically."""
        clean_month = month.strip()
        budgets = self.get_all()
        budgets[clean_month] = amount

        try:
            temp_file = tempfile.NamedTemporaryFile("w", dir=self.data_dir, delete=False, encoding="utf-8")
            temp_path = Path(temp_file.name)
            try:
                with temp_file:
                    for m, amt in sorted(budgets.items()):
                        temp_file.write(json.dumps({"month": m, "amount": amt}, ensure_ascii=False) + "\n")
                os.replace(temp_path, self.file_path)
            except Exception:
                if temp_path.exists():
                    temp_path.unlink()
                raise
        except OSError as e:
            raise BudgetAppIOError(
                f"예산 저장 실패: {e}",
                hint=f"저장 파일 권한을 확인하세요: {self.file_path}"
            )

