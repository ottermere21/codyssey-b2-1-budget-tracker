"""Tests for file-based repository layer and streaming generators."""
import tempfile
import unittest
from pathlib import Path

from budget_app.models import Transaction
from budget_app.repository import (
    TransactionRepository,
    CategoryRepository,
    BudgetRepository,
    reverse_readline_generator,
    forward_readline_generator,
)


class TestRepository(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_reverse_readline_generator(self):
        test_file = self.data_dir / "test_reverse.txt"
        lines = [f"line_{i}" for i in range(100)]
        test_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = list(reverse_readline_generator(test_file, buffer_size=32))
        expected = list(reversed(lines))
        self.assertEqual(result, expected)

    def test_forward_readline_generator(self):
        test_file = self.data_dir / "test_forward.txt"
        lines = ["apple", "banana", "cherry"]
        test_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = list(forward_readline_generator(test_file))
        self.assertEqual(result, lines)

    def test_transaction_repository_crud(self):
        repo = TransactionRepository(self.data_dir)
        self.assertEqual(repo.get_next_id(), "TX-000001")

        tx1 = Transaction("TX-000001", "2024-01-10", "income", 100000, "salary", "급여", ["pay"])
        repo.add(tx1)

        self.assertEqual(repo.get_next_id(), "TX-000002")

        tx2 = Transaction("TX-000002", "2024-01-11", "expense", 20000, "food", "저녁", [])
        repo.add(tx2)

        # Reverse streaming
        streamed = list(repo.stream_all(reverse=True))
        self.assertEqual(len(streamed), 2)
        self.assertEqual(streamed[0].id, "TX-000002")
        self.assertEqual(streamed[1].id, "TX-000001")

        # Find by ID
        found = repo.find_by_id("TX-000001")
        self.assertIsNotNone(found)
        self.assertEqual(found.amount, 100000)

        # Update
        tx1_updated = Transaction("TX-000001", "2024-01-10", "income", 150000, "salary", "수정급여", ["pay"])
        success = repo.update(tx1_updated)
        self.assertTrue(success)
        rechecked = repo.find_by_id("TX-000001")
        self.assertEqual(rechecked.amount, 150000)

        # Delete
        del_success = repo.delete("TX-000002")
        self.assertTrue(del_success)
        self.assertIsNone(repo.find_by_id("TX-000002"))
        self.assertEqual(len(list(repo.stream_all())), 1)

    def test_category_repository(self):
        cat_repo = CategoryRepository(self.data_dir)
        categories = cat_repo.get_all()
        self.assertIn("food", categories)
        self.assertIn("transport", categories)

        cat_repo.add("health")
        self.assertTrue(cat_repo.exists("health"))
        self.assertTrue(cat_repo.exists("HEALTH"))

        removed = cat_repo.remove("health")
        self.assertTrue(removed)
        self.assertFalse(cat_repo.exists("health"))

    def test_budget_repository(self):
        budget_repo = BudgetRepository(self.data_dir)
        self.assertIsNone(budget_repo.get_budget("2024-01"))

        budget_repo.set_budget("2024-01", 500000)
        self.assertEqual(budget_repo.get_budget("2024-01"), 500000)

        all_budgets = budget_repo.get_all()
        self.assertEqual(all_budgets["2024-01"], 500000)


if __name__ == "__main__":
    unittest.main()

