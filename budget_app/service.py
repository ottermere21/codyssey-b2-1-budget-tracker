"""Business logic and service layer for Budget App."""
import csv
from collections import defaultdict
from pathlib import Path
from typing import Generator, List, Optional, Tuple, Dict, Any

from budget_app.decorators import timed_execution
from budget_app.exceptions import (
    ValidationError,
    NotFoundError,
    DuplicateError,
    CategoryInUseError,
    BudgetAppIOError,
)
from budget_app.models import Transaction, SummaryResult
from budget_app.repository import (
    TransactionRepository,
    CategoryRepository,
    BudgetRepository,
)
from budget_app.validator import (
    validate_date,
    validate_month,
    validate_type,
    validate_amount,
    validate_category_name,
    parse_tags,
)


class BudgetService:
    """Service handling budget tracking business logic and validation."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.tx_repo = TransactionRepository(self.data_dir)
        self.cat_repo = CategoryRepository(self.data_dir)
        self.budget_repo = BudgetRepository(self.data_dir)

    # ----------------- Transaction Management -----------------

    @timed_execution("add_transaction")
    def add_transaction(
        self,
        date_str: str,
        type_str: str,
        category: str,
        amount_val: Any,
        memo: str = "",
        tags_input: Any = None,
    ) -> Transaction:
        """Validate and add a new transaction."""
        valid_date = validate_date(date_str)
        valid_type = validate_type(type_str)
        valid_amount = validate_amount(amount_val)
        valid_category = validate_category_name(category)

        # Check registered categories
        available_categories = self.cat_repo.get_all()
        matched_cat = None
        for cat in available_categories:
            if cat.lower() == valid_category.lower():
                matched_cat = cat
                break

        if not matched_cat:
            cat_list = ", ".join(available_categories)
            raise ValidationError(
                f"등록되지 않은 카테고리입니다: '{valid_category}'",
                hint=f"등록된 카테고리 목록: [{cat_list}]\n'category add' 명령으로 새 카테고리를 먼저 등록할 수 있습니다."
            )

        parsed_tags = parse_tags(tags_input)
        clean_memo = str(memo).strip() if memo else ""

        tx_id = self.tx_repo.get_next_id()
        transaction = Transaction(
            id=tx_id,
            date=valid_date,
            type=valid_type,
            amount=valid_amount,
            category=matched_cat,
            memo=clean_memo,
            tags=parsed_tags,
        )

        self.tx_repo.add(transaction)
        return transaction

    def list_transactions(self, limit: int = 20) -> Generator[Transaction, None, None]:
        """Stream transactions in reverse chronological order (newest first)."""
        if limit <= 0:
            raise ValidationError("조회 개수(--limit)는 1 이상이어야 합니다.", hint="예: --limit 10")

        count = 0
        for tx in self.tx_repo.stream_all(reverse=True):
            yield tx
            count += 1
            if count >= limit:
                break

    def search_transactions(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        category: Optional[str] = None,
        type_filter: Optional[str] = None,
        query: Optional[str] = None,
        tag: Optional[str] = None,
    ) -> Generator[Transaction, None, None]:
        """Search transactions by multiple criteria with streaming (newest first)."""
        valid_from = validate_date(from_date) if from_date else None
        valid_to = validate_date(to_date) if to_date else None
        valid_type = validate_type(type_filter) if type_filter else None
        clean_cat = category.strip().lower() if category else None
        clean_query = query.strip().lower() if query else None
        clean_tag = tag.strip().lower() if tag else None

        if valid_from and valid_to and valid_from > valid_to:
            raise ValidationError(
                f"시작 날짜({valid_from})가 종료 날짜({valid_to})보다 늦습니다.",
                hint="시작일은 종료일보다 이전이거나 같아야 합니다."
            )

        for tx in self.tx_repo.stream_all(reverse=True):
            if valid_from and tx.date < valid_from:
                continue
            if valid_to and tx.date > valid_to:
                continue
            if valid_type and tx.type != valid_type:
                continue
            if clean_cat and tx.category.lower() != clean_cat:
                continue
            if clean_query and clean_query not in tx.memo.lower():
                continue
            if clean_tag and not any(t.lower() == clean_tag for t in tx.tags):
                continue
            yield tx

    def update_transaction(
        self,
        tx_id: str,
        date_str: Optional[str] = None,
        type_str: Optional[str] = None,
        category: Optional[str] = None,
        amount_val: Any = None,
        memo: Optional[str] = None,
        tags_input: Any = None,
    ) -> Transaction:
        """Update an existing transaction."""
        target_tx = self.tx_repo.find_by_id(tx_id)
        if not target_tx:
            raise NotFoundError(
                f"존재하지 않는 거래 ID입니다: '{tx_id}'",
                hint="거래 목록(list)을 확인하여 올바른 ID를 입력하세요."
            )

        new_date = validate_date(date_str) if date_str is not None else target_tx.date
        new_type = validate_type(type_str) if type_str is not None else target_tx.type
        new_amount = validate_amount(amount_val) if amount_val is not None else target_tx.amount

        new_category = target_tx.category
        if category is not None:
            valid_category = validate_category_name(category)
            available_categories = self.cat_repo.get_all()
            matched = next((c for c in available_categories if c.lower() == valid_category.lower()), None)
            if not matched:
                cat_list = ", ".join(available_categories)
                raise ValidationError(
                    f"등록되지 않은 카테고리입니다: '{valid_category}'",
                    hint=f"등록된 카테고리 목록: [{cat_list}]"
                )
            new_category = matched

        new_memo = str(memo).strip() if memo is not None else target_tx.memo
        new_tags = parse_tags(tags_input) if tags_input is not None else target_tx.tags

        updated_tx = Transaction(
            id=target_tx.id,
            date=new_date,
            type=new_type,
            amount=new_amount,
            category=new_category,
            memo=new_memo,
            tags=new_tags,
        )

        success = self.tx_repo.update(updated_tx)
        if not success:
            raise NotFoundError(
                f"거래 내역 수정 실패: ID '{tx_id}'를 찾을 수 없습니다.",
                hint="데이터 파일 상태를 확인하세요."
            )
        return updated_tx

    def delete_transaction(self, tx_id: str) -> None:
        """Delete an existing transaction."""
        target_tx = self.tx_repo.find_by_id(tx_id)
        if not target_tx:
            raise NotFoundError(
                f"존재하지 않는 거래 ID입니다: '{tx_id}'",
                hint="거래 목록(list)을 확인하여 올바른 ID를 입력하세요."
            )

        success = self.tx_repo.delete(tx_id)
        if not success:
            raise NotFoundError(
                f"거래 내역 삭제 실패: ID '{tx_id}'를 찾을 수 없습니다.",
                hint="데이터 파일 상태를 확인하세요."
            )

    # ----------------- Summary & Budget -----------------

    @timed_execution("get_summary")
    def get_summary(self, month_str: str, top_n: int = 5) -> SummaryResult:
        """Calculate monthly income, expense, balance, and category breakdown."""
        valid_month = validate_month(month_str)
        if top_n <= 0:
            raise ValidationError("TOP N 개수는 1 이상이어야 합니다.", hint="예: --top 3")

        total_income = 0
        total_expense = 0
        category_expense_map: Dict[str, int] = defaultdict(int)
        has_any_data = False

        # Stream all transactions and filter by month
        for tx in self.tx_repo.stream_all(reverse=False):
            if tx.date.startswith(valid_month):
                has_any_data = True
                if tx.type == "income":
                    total_income += tx.amount
                elif tx.type == "expense":
                    total_expense += tx.amount
                    category_expense_map[tx.category] += tx.amount

        budget_amount = self.budget_repo.get_budget(valid_month)

        sorted_categories = sorted(category_expense_map.items(), key=lambda x: x[1], reverse=True)[:top_n]

        return SummaryResult(
            month=valid_month,
            total_income=total_income,
            total_expense=total_expense,
            balance=total_income - total_expense,
            category_expenses=sorted_categories,
            budget_amount=budget_amount,
            has_data=has_any_data,
        )

    def set_budget(self, month_str: str, amount_val: Any) -> int:
        """Set monthly budget."""
        valid_month = validate_month(month_str)
        valid_amount = validate_amount(amount_val)
        self.budget_repo.set_budget(valid_month, valid_amount)
        return valid_amount

    def get_budget(self, month_str: str) -> Optional[int]:
        """Get budget for a specific month."""
        valid_month = validate_month(month_str)
        return self.budget_repo.get_budget(valid_month)

    def get_all_budgets(self) -> Dict[str, int]:
        """Get all registered budgets."""
        return self.budget_repo.get_all()

    # ----------------- Category Management -----------------

    def add_category(self, name: str) -> str:
        """Add a new category."""
        clean_name = validate_category_name(name)
        if self.cat_repo.exists(clean_name):
            raise DuplicateError(
                f"이미 존재하는 카테고리입니다: '{clean_name}'",
                hint="다른 이름을 입력하거나 'category list'로 확인하세요."
            )
        self.cat_repo.add(clean_name)
        return clean_name

    def list_categories(self) -> List[str]:
        """List all registered categories."""
        return self.cat_repo.get_all()

    def remove_category(self, name: str) -> str:
        """Remove a category if not in use by any transaction."""
        clean_name = validate_category_name(name)
        if not self.cat_repo.exists(clean_name):
            raise NotFoundError(
                f"존재하지 않는 카테고리입니다: '{clean_name}'",
                hint="'category list' 명령어로 현재 등록된 카테고리를 확인하세요."
            )

        # Check if any transaction is using this category
        in_use_count = 0
        for tx in self.tx_repo.stream_all(reverse=False):
            if tx.category.lower() == clean_name.lower():
                in_use_count += 1

        if in_use_count > 0:
            raise CategoryInUseError(
                f"카테고리 '{clean_name}'를 사용하는 거래 내역이 {in_use_count}건 존재하여 삭제할 수 없습니다.",
                hint="해당 카테고리의 거래 내역을 먼저 다른 카테고리로 변경(update)하거나 삭제(delete)하세요."
            )

        self.cat_repo.remove(clean_name)
        return clean_name

    # ----------------- Import / Export -----------------

    @timed_execution("export_csv")
    def export_csv(
        self,
        out_path: str,
        month: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> int:
        """Export transactions matching criteria to CSV file."""
        if not month and not (from_date or to_date):
            raise ValidationError(
                "내보내기 조건을 하나 이상 지정해야 합니다.",
                hint="--month YYYY-MM 또는 --from YYYY-MM-DD (--to YYYY-MM-DD) 옵션을 입력하세요."
            )

        valid_month = validate_month(month) if month else None
        valid_from = validate_date(from_date) if from_date else None
        valid_to = validate_date(to_date) if to_date else None

        if valid_from and valid_to and valid_from > valid_to:
            raise ValidationError(
                f"시작 날짜({valid_from})가 종료 날짜({valid_to})보다 늦습니다.",
                hint="시작일은 종료일보다 이전이거나 같아야 합니다."
            )

        out_file = Path(out_path)
        try:
            out_file.parent.mkdir(parents=True, exist_ok=True)
            count = 0
            with open(out_file, "w", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                # Header as per requirement: date,type,category,amount,memo,tags
                writer.writerow(["date", "type", "category", "amount", "memo", "tags"])

                # Filter and stream transactions
                for tx in self.tx_repo.stream_all(reverse=False):
                    if valid_month and not tx.date.startswith(valid_month):
                        continue
                    if valid_from and tx.date < valid_from:
                        continue
                    if valid_to and tx.date > valid_to:
                        continue

                    tags_str = ",".join(tx.tags)
                    writer.writerow([tx.date, tx.type, tx.category, tx.amount, tx.memo, tags_str])
                    count += 1

            return count
        except OSError as e:
            raise BudgetAppIOError(
                f"CSV 내보내기 실패: {e}",
                hint=f"출력 경로 권한 및 파일명을 확인하세요: {out_path}"
            )

    @timed_execution("import_csv")
    def import_csv(self, from_path: str) -> Tuple[int, int]:
        """Import transactions from CSV file. Returns (imported_count, skipped_count)."""
        csv_file = Path(from_path)
        if not csv_file.exists():
            raise NotFoundError(
                f"가져올 CSV 파일을 찾을 수 없습니다: '{from_path}'",
                hint="파일 경로가 올바른지 확인하세요."
            )

        imported_count = 0
        skipped_count = 0
        available_categories = {c.lower(): c for c in self.cat_repo.get_all()}

        try:
            with open(csv_file, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                if not reader.fieldnames:
                    raise ValidationError(
                        "CSV 파일이 비어있거나 올바른 형식이 아닙니다.",
                        hint="헤더 행(date,type,category,amount,memo,tags)을 포함해야 합니다."
                    )

                fieldnames = [fn.strip().lower() for fn in reader.fieldnames if fn]
                required_fields = ["date", "type", "category", "amount"]
                for req in required_fields:
                    if req not in fieldnames:
                        raise ValidationError(
                            f"CSV 헤더에 필수 컬럼 '{req}'가 누락되었습니다.",
                            hint="date, type, category, amount, memo, tags 컬럼을 포함해야 합니다."
                        )

                for row_idx, row in enumerate(reader, start=2):
                    try:
                        clean_row = {k.strip().lower(): v.strip() for k, v in row.items() if k is not None and v is not None}
                        date_val = clean_row.get("date", "")
                        type_val = clean_row.get("type", "")
                        cat_val = clean_row.get("category", "")
                        amount_val = clean_row.get("amount", "")
                        memo_val = clean_row.get("memo", "")
                        tags_val = clean_row.get("tags", "")

                        valid_date = validate_date(date_val)
                        valid_type = validate_type(type_val)
                        valid_amount = validate_amount(amount_val)

                        # Category validation
                        cat_lower = cat_val.lower()
                        if cat_lower not in available_categories:
                            skipped_count += 1
                            continue
                        matched_cat = available_categories[cat_lower]

                        parsed_tags = parse_tags(tags_val)
                        tx_id = self.tx_repo.get_next_id()
                        new_tx = Transaction(
                            id=tx_id,
                            date=valid_date,
                            type=valid_type,
                            amount=valid_amount,
                            category=matched_cat,
                            memo=memo_val,
                            tags=parsed_tags,
                        )
                        self.tx_repo.add(new_tx)
                        imported_count += 1
                    except Exception:
                        skipped_count += 1

            return imported_count, skipped_count
        except OSError as e:
            raise BudgetAppIOError(
                f"CSV 가져오기 실패: {e}",
                hint=f"파일 접근 권한을 확인하세요: {from_path}"
            )

