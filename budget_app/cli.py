"""Command Line Interface (CLI) for Budget App."""
import argparse
import sys
from pathlib import Path
from typing import List, Optional

from budget_app.decorators import handle_cli_errors
from budget_app.exceptions import ValidationError
from budget_app.models import Transaction
from budget_app.service import BudgetService


def format_transaction_line(tx: Transaction) -> str:
    """Format a transaction record for list/search output."""
    parts = [
        tx.id,
        tx.date,
        tx.type,
        tx.category,
        str(tx.amount),
        tx.memo,
    ]
    if tx.tags:
        parts.append(f"[{','.join(tx.tags)}]")
    return " | ".join(parts)


def prompt_input_with_validation(prompt_text: str, validator_fn, hint_text: str = "") -> str:
    """Interactively prompt user with continuous validation loop."""
    while True:
        try:
            val = input(prompt_text)
            validated = validator_fn(val)
            return validated
        except ValidationError as e:
            sys.stderr.write(f"{e}\n")
        except EOFError:
            raise ValidationError("입력이 조기 종료되었습니다.", hint="정상적인 입력을 입력해주세요.")


class BudgetCLI:
    """CLI Controller for dispatching and executing commands."""

    def __init__(self, service: BudgetService):
        self.service = service

    def cmd_add(self, args: argparse.Namespace) -> None:
        """Handle interactive transaction creation."""
        categories = self.service.list_categories()
        if not categories:
            sys.stderr.write("[오류] 등록된 카테고리가 없습니다.\n")
            sys.stderr.write("[힌트] 'category add' 명령어로 카테고리를 먼저 등록하세요.\n")
            sys.exit(1)

        # 1. Date
        from budget_app.validator import validate_date, validate_type, validate_amount

        date_val = prompt_input_with_validation(
            "날짜(YYYY-MM-DD): ",
            validate_date,
            "예: 2024-01-15"
        )

        # 2. Type
        type_val = prompt_input_with_validation(
            "타입(income/expense): ",
            validate_type,
            "income 또는 expense 중 하나를 입력하세요."
        )

        # 3. Category
        def _check_category(cat_str: str) -> str:
            clean = cat_str.strip()
            if not clean:
                raise ValidationError("카테고리를 입력해주세요.", hint=f"선택 가능: {', '.join(categories)}")
            matched = next((c for c in categories if c.lower() == clean.lower()), None)
            if not matched:
                raise ValidationError(
                    f"존재하지 않는 카테고리입니다: '{clean}'",
                    hint=f"등록된 카테고리: {', '.join(categories)}"
                )
            return matched

        category_val = prompt_input_with_validation(
            "카테고리: ",
            _check_category,
            f"등록된 카테고리: {', '.join(categories)}"
        )

        # 4. Amount
        amount_val = prompt_input_with_validation(
            "금액(양수): ",
            validate_amount,
            "1원 이상의 정수 금액을 입력하세요."
        )

        # 5. Memo
        memo_val = input("메모(선택): ").strip()

        # 6. Tags
        tags_input = input("태그(쉼표로 구분, 없으면 엔터): ").strip()

        created_tx = self.service.add_transaction(
            date_str=date_val,
            type_str=type_val,
            category=category_val,
            amount_val=amount_val,
            memo=memo_val,
            tags_input=tags_input,
        )

        print(f"[저장 완료] id={created_tx.id}")

    def cmd_list(self, args: argparse.Namespace) -> None:
        """Handle listing transactions with limit."""
        limit = args.limit if args.limit is not None else 20
        transactions = list(self.service.list_transactions(limit=limit))
        if not transactions:
            print("등록된 거래 내역이 없습니다.")
            return

        for tx in transactions:
            print(format_transaction_line(tx))

    def cmd_search(self, args: argparse.Namespace) -> None:
        """Handle searching transactions."""
        matched = list(self.service.search_transactions(
            from_date=args.from_date,
            to_date=args.to_date,
            category=args.category,
            type_filter=args.type,
            query=args.q,
            tag=args.tag,
        ))

        if not matched:
            print("조건에 일치하는 거래 내역이 없습니다.")
            return

        for tx in matched:
            print(format_transaction_line(tx))

    def cmd_summary(self, args: argparse.Namespace) -> None:
        """Handle monthly summary and budget warning."""
        month = args.month
        top_n = args.top if args.top is not None else 3

        result = self.service.get_summary(month_str=month, top_n=top_n)

        if not result.has_data and result.budget_amount is None:
            print(f"{month} 데이터가 없습니다.")
            return

        print(f"총 수입: {result.total_income}원")
        print(f"총 지출: {result.total_expense}원")
        print(f"잔액: {result.balance}원")

        if result.budget_amount is not None:
            rate_str = f"{result.usage_rate:.1f}%" if result.usage_rate is not None else "0.0%"
            print(f"예산: {result.budget_amount}원 (사용률 {rate_str})")
            if result.is_over_budget:
                diff = result.total_expense - result.budget_amount
                print(f"[경고] 예산을 초과했습니다! (초과액: {diff}원)")

        if result.category_expenses:
            print(f"\n지출 TOP {len(result.category_expenses)}:")
            for rank, (cat_name, amount) in enumerate(result.category_expenses, 1):
                print(f"{rank}) {cat_name} {amount}원")

    def cmd_budget(self, args: argparse.Namespace) -> None:
        """Handle budget setting and viewing."""
        subcmd = args.budget_subcommand
        if subcmd == "set":
            if not args.month or args.amount is None:
                raise ValidationError(
                    "예산 설정 시 --month 와 --amount 옵션이 모두 필요합니다.",
                    hint="예: python -m budget_app budget set --month 2024-01 --amount 500000"
                )
            amount = self.service.set_budget(args.month, args.amount)
            print(f"[저장 완료] {args.month} 예산 {amount}원")
        elif subcmd == "list":
            budgets = self.service.get_all_budgets()
            if not budgets:
                print("설정된 예산이 없습니다.")
                return
            for m, amt in sorted(budgets.items()):
                print(f"- {m}: {amt}원")
        else:
            raise ValidationError(
                f"알 수 없는 예산 하위 명령입니다: '{subcmd}'",
                hint="budget set 또는 budget list 를 사용하세요."
            )

    def cmd_category(self, args: argparse.Namespace) -> None:
        """Handle category management."""
        subcmd = args.category_subcommand
        if subcmd == "add":
            name = args.name
            if not name:
                name = input("카테고리명: ").strip()
            saved_name = self.service.add_category(name)
            print(f"[저장 완료] category={saved_name}")
        elif subcmd == "list":
            categories = self.service.list_categories()
            if not categories:
                print("등록된 카테고리가 없습니다.")
                return
            for cat in categories:
                print(f"- {cat}")
        elif subcmd == "remove":
            name = args.name
            if not name:
                name = input("삭제할 카테고리명: ").strip()
            removed_name = self.service.remove_category(name)
            print(f"[삭제 완료] category={removed_name}")
        else:
            raise ValidationError(
                f"알 수 없는 카테고리 하위 명령입니다: '{subcmd}'",
                hint="category add, category list, category remove 중 하나를 사용하세요."
            )

    def cmd_update(self, args: argparse.Namespace) -> None:
        """Handle transaction update (Option A: CLI flags based)."""
        if not args.id:
            raise ValidationError("수정할 거래 ID(--id)를 지정해야 합니다.", hint="예: update --id TX-000001")

        # Check if at least one field is provided for update
        update_fields = [args.date, args.type, args.category, args.amount, args.memo, args.tags]
        if all(f is None for f in update_fields):
            raise ValidationError(
                "수정할 항목을 하나 이상 지정해야 합니다.",
                hint="--date, --type, --category, --amount, --memo, --tags 옵션 중 수정할 항목을 입력하세요."
            )

        updated_tx = self.service.update_transaction(
            tx_id=args.id,
            date_str=args.date,
            type_str=args.type,
            category=args.category,
            amount_val=args.amount,
            memo=args.memo,
            tags_input=args.tags,
        )
        print(f"[수정 완료] id={updated_tx.id}")

    def cmd_delete(self, args: argparse.Namespace) -> None:
        """Handle transaction deletion."""
        if not args.id:
            raise ValidationError("삭제할 거래 ID(--id)를 지정해야 합니다.", hint="예: delete --id TX-000001")

        self.service.delete_transaction(args.id)
        print(f"[삭제 완료] id={args.id}")

    def cmd_export(self, args: argparse.Namespace) -> None:
        """Handle CSV export."""
        if not args.out:
            raise ValidationError("출력할 CSV 파일 경로(--out)를 지정해야 합니다.", hint="예: export --out export.csv --month 2024-01")

        count = self.service.export_csv(
            out_path=args.out,
            month=args.month,
            from_date=args.from_date,
            to_date=args.to_date,
        )
        print(f"[완료] {args.out} ({count} records)")

    def cmd_import(self, args: argparse.Namespace) -> None:
        """Handle CSV import."""
        if not args.from_file:
            raise ValidationError("가져올 CSV 파일 경로(--from)를 지정해야 합니다.", hint="예: import --from import.csv")

        imported_count, skipped_count = self.service.import_csv(args.from_file)
        print(f"[완료] imported={imported_count}, skipped={skipped_count}")


def create_parser() -> argparse.ArgumentParser:
    """Create top-level CLI argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog="budget_app",
        description="콘솔 기반 가계부 서비스 (Budget App)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--data-dir",
        default="./data",
        help="데이터 저장 디렉토리 경로 (기본값: ./data)",
    )

    subparsers = parser.add_subparsers(dest="command", help="실행할 명령어")

    # 1. add
    subparsers.add_parser("add", help="대화형으로 새 거래 추가")

    # 2. list
    list_p = subparsers.add_parser("list", help="최신순 거래 목록 조회")
    list_p.add_argument("--limit", type=int, default=20, help="조회할 거래 건수 (기본값: 20)")

    # 3. search
    search_p = subparsers.add_parser("search", help="조건별 거래 검색")
    search_p.add_argument("--from", dest="from_date", help="시작 날짜 (YYYY-MM-DD)")
    search_p.add_argument("--to", dest="to_date", help="종료 날짜 (YYYY-MM-DD)")
    search_p.add_argument("--category", help="카테고리")
    search_p.add_argument("--type", help="거래 타입 (income/expense)")
    search_p.add_argument("--q", help="메모 검색어")
    search_p.add_argument("--tag", help="태그")

    # 4. summary
    summary_p = subparsers.add_parser("summary", help="월별 수입/지출 요약 및 예산 확인")
    summary_p.add_argument("--month", required=True, help="조회할 월 (YYYY-MM)")
    summary_p.add_argument("--top", type=int, default=3, help="지출 상위 카테고리 개수 (기본값: 3)")

    # 5. budget
    budget_p = subparsers.add_parser("budget", help="월별 예산 설정 및 조회")
    budget_subs = budget_p.add_subparsers(dest="budget_subcommand", help="예산 명령")
    budget_set_p = budget_subs.add_parser("set", help="월별 예산 설정")
    budget_set_p.add_argument("--month", required=True, help="설정할 월 (YYYY-MM)")
    budget_set_p.add_argument("--amount", type=int, required=True, help="예산 금액 (양수 정수)")
    budget_subs.add_parser("list", help="등록된 예산 목록 조회")

    # 6. category
    cat_p = subparsers.add_parser("category", help="카테고리 관리")
    cat_subs = cat_p.add_subparsers(dest="category_subcommand", help="카테고리 명령")
    cat_add_p = cat_subs.add_parser("add", help="카테고리 추가")
    cat_add_p.add_argument("name", nargs="?", default=None, help="추가할 카테고리명 (생략 시 대화형 입력)")
    cat_subs.add_parser("list", help="카테고리 목록 조회")
    cat_rem_p = cat_subs.add_parser("remove", help="카테고리 삭제")
    cat_rem_p.add_argument("name", nargs="?", default=None, help="삭제할 카테고리명 (생략 시 대화형 입력)")

    # 7. update
    update_p = subparsers.add_parser("update", help="거래 수정 (옵션 기반)")
    update_p.add_argument("--id", required=True, help="수정할 거래 ID")
    update_p.add_argument("--date", help="새 날짜 (YYYY-MM-DD)")
    update_p.add_argument("--type", help="새 타입 (income/expense)")
    update_p.add_argument("--category", help="새 카테고리")
    update_p.add_argument("--amount", type=int, help="새 금액 (양수 정수)")
    update_p.add_argument("--memo", help="새 메모")
    update_p.add_argument("--tags", help="새 태그 (쉼표 구분)")

    # 8. delete
    del_p = subparsers.add_parser("delete", help="거래 삭제")
    del_p.add_argument("--id", required=True, help="삭제할 거래 ID")

    # 9. export
    export_p = subparsers.add_parser("export", help="CSV 파일로 거래 내역 내보내기")
    export_p.add_argument("--out", required=True, help="저장할 CSV 파일 경로")
    export_p.add_argument("--month", help="내보낼 월 (YYYY-MM)")
    export_p.add_argument("--from", dest="from_date", help="시작 날짜 (YYYY-MM-DD)")
    export_p.add_argument("--to", dest="to_date", help="종료 날짜 (YYYY-MM-DD)")

    # 10. import
    import_p = subparsers.add_parser("import", help="CSV 파일에서 거래 내역 가져오기")
    import_p.add_argument("--from", dest="from_file", required=True, help="가져올 CSV 파일 경로")

    return parser


@handle_cli_errors
def main(argv: Optional[List[str]] = None) -> None:
    """Main CLI entrypoint wrapped with error handling decorator."""
    parser = create_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        sys.exit(0)

    service = BudgetService(data_dir=Path(args.data_dir))
    cli = BudgetCLI(service)

    command_map = {
        "add": cli.cmd_add,
        "list": cli.cmd_list,
        "search": cli.cmd_search,
        "summary": cli.cmd_summary,
        "budget": cli.cmd_budget,
        "category": cli.cmd_category,
        "update": cli.cmd_update,
        "delete": cli.cmd_delete,
        "export": cli.cmd_export,
        "import": cli.cmd_import,
    }

    handler = command_map.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()

