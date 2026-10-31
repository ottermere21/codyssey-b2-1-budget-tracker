"""Tests for CLI end-to-end functionality."""
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from budget_app.cli import main


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = self.temp_dir.name

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_cli(self, args, inputs=None):
        """Helper to run CLI and capture stdout/stderr."""
        cli_args = ["--data-dir", self.data_dir] + args
        stdout = io.StringIO()
        stderr = io.StringIO()

        with patch("sys.stdout", stdout), patch("sys.stderr", stderr):
            if inputs:
                with patch("builtins.input", side_effect=inputs):
                    try:
                        main(cli_args)
                        exit_code = 0
                    except SystemExit as e:
                        exit_code = e.code if isinstance(e.code, int) else 1
            else:
                try:
                    main(cli_args)
                    exit_code = 0
                except SystemExit as e:
                    exit_code = e.code if isinstance(e.code, int) else 1

        return exit_code, stdout.getvalue(), stderr.getvalue()

    def test_cli_add_and_list(self):
        # 1. Add interactive
        inputs = [
            "2024-01-15",  # date
            "expense",     # type
            "food",        # category
            "15000",       # amount
            "점심",        # memo
            "meal",        # tags
        ]
        code, out, err = self.run_cli(["add"], inputs=inputs)
        self.assertEqual(code, 0)
        self.assertIn("[저장 완료] id=TX-000001", out)

        # 2. List
        code, out, err = self.run_cli(["list", "--limit", "10"])
        self.assertEqual(code, 0)
        self.assertIn("TX-000001 | 2024-01-15 | expense | food | 15000 | 점심", out)

    def test_cli_category(self):
        # category list
        code, out, err = self.run_cli(["category", "list"])
        self.assertEqual(code, 0)
        self.assertIn("- food", out)

        # category add
        code, out, err = self.run_cli(["category", "add", "books"])
        self.assertEqual(code, 0)
        self.assertIn("[저장 완료] category=books", out)

        # category remove
        code, out, err = self.run_cli(["category", "remove", "books"])
        self.assertEqual(code, 0)
        self.assertIn("[삭제 완료] category=books", out)

    def test_cli_budget_and_summary(self):
        # Add income and expense
        self.run_cli(["add"], inputs=["2024-01-10", "income", "salary", "3000000", "급여", ""])
        self.run_cli(["add"], inputs=["2024-01-15", "expense", "food", "45000", "식사", ""])

        # Set budget
        code, out, err = self.run_cli(["budget", "set", "--month", "2024-01", "--amount", "500000"])
        self.assertEqual(code, 0)
        self.assertIn("[저장 완료] 2024-01 예산 500000원", out)

        # Summary
        code, out, err = self.run_cli(["summary", "--month", "2024-01", "--top", "3"])
        self.assertEqual(code, 0)
        self.assertIn("총 수입: 3000000원", out)
        self.assertIn("총 지출: 45000원", out)
        self.assertIn("잔액: 2955000원", out)
        self.assertIn("예산: 500000원 (사용률 9.0%)", out)

    def test_cli_update_and_delete(self):
        # Add tx
        self.run_cli(["add"], inputs=["2024-01-15", "expense", "food", "15000", "점심", ""])

        # Update
        code, out, err = self.run_cli(["update", "--id", "TX-000001", "--amount", "20000", "--memo", "비싼 점심"])
        self.assertEqual(code, 0)
        self.assertIn("[수정 완료] id=TX-000001", out)

        # Check list
        code, out, err = self.run_cli(["list"])
        self.assertIn("20000", out)
        self.assertIn("비싼 점심", out)

        # Delete
        code, out, err = self.run_cli(["delete", "--id", "TX-000001"])
        self.assertEqual(code, 0)
        self.assertIn("[삭제 완료] id=TX-000001", out)

    def test_cli_error_output_and_exit_code(self):
        # Invalid date in search or delete non-existent ID
        code, out, err = self.run_cli(["delete", "--id", "TX-999999"])
        self.assertEqual(code, 1)
        self.assertIn("[오류] 존재하지 않는 거래 ID입니다: 'TX-999999'", err)
        self.assertIn("[힌트]", err)

    def test_cli_export_import(self):
        self.run_cli(["add"], inputs=["2024-01-15", "expense", "food", "15000", "점심", "meal"])
        csv_path = Path(self.data_dir) / "exported.csv"

        # Export
        code, out, err = self.run_cli(["export", "--out", str(csv_path), "--month", "2024-01"])
        self.assertEqual(code, 0)
        self.assertIn("(1 records)", out)

        # Import into fresh directory
        fresh_dir = tempfile.TemporaryDirectory()
        cli_args = ["--data-dir", fresh_dir.name, "import", "--from", str(csv_path)]
        stdout = io.StringIO()
        with patch("sys.stdout", stdout):
            main(cli_args)
        self.assertIn("imported=1, skipped=0", stdout.getvalue())
        fresh_dir.cleanup()


if __name__ == "__main__":
    unittest.main()

