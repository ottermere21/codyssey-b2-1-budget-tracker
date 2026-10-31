"""Tests for service layer."""
import tempfile
import unittest
from pathlib import Path

from budget_app.exceptions import ValidationError, NotFoundError, CategoryInUseError
from budget_app.service import BudgetService


class TestBudgetService(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)
        self.service = BudgetService(self.data_dir)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_add_and_list_transaction(self):
        tx = self.service.add_transaction(
            date_str="2024-01-15",
            type_str="expense",
            category="food",
            amount_val=15000,
            memo="점심",
            tags_input="meal",
        )
        self.assertEqual(tx.id, "TX-000001")
        self.assertEqual(tx.amount, 15000)

        # Unregistered category raises error
        with self.assertRaises(ValidationError):
            self.service.add_transaction("2024-01-15", "expense", "unregistered", 1000)

        # Listing
        items = list(self.service.list_transactions(limit=10))
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, "TX-000001")

    def test_search_transactions(self):
        self.service.add_transaction("2024-01-10", "income", "salary", 3000000, "월급", "main")
        self.service.add_transaction("2024-01-12", "expense", "transport", 20000, "지하철", "subway")
        self.service.add_transaction("2024-01-15", "expense", "food", 15000, "점심", "meal")

        # By type
        incomes = list(self.service.search_transactions(type_filter="income"))
        self.assertEqual(len(incomes), 1)
        self.assertEqual(incomes[0].category, "salary")

        # By date range
        date_filtered = list(self.service.search_transactions(from_date="2024-01-11", to_date="2024-01-13"))
        self.assertEqual(len(date_filtered), 1)
        self.assertEqual(date_filtered[0].memo, "지하철")

        # By query
        q_filtered = list(self.service.search_transactions(query="점심"))
        self.assertEqual(len(q_filtered), 1)

        # By tag
        tag_filtered = list(self.service.search_transactions(tag="subway"))
        self.assertEqual(len(tag_filtered), 1)

    def test_update_and_delete_transaction(self):
        tx = self.service.add_transaction("2024-01-15", "expense", "food", 15000, "점심")

        # Update
        updated = self.service.update_transaction(tx.id, amount_val=20000, memo="비싼 점심")
        self.assertEqual(updated.amount, 20000)
        self.assertEqual(updated.memo, "비싼 점심")

        # Update non-existent
        with self.assertRaises(NotFoundError):
            self.service.update_transaction("TX-999999", amount_val=10000)

        # Delete
        self.service.delete_transaction(tx.id)
        with self.assertRaises(NotFoundError):
            self.service.delete_transaction(tx.id)

    def test_category_in_use_protection(self):
        self.service.add_transaction("2024-01-15", "expense", "food", 15000)

        # Removing category 'food' should raise CategoryInUseError
        with self.assertRaises(CategoryInUseError):
            self.service.remove_category("food")

        # Add unused category and remove successfully
        self.service.add_category("custom_cat")
        removed = self.service.remove_category("custom_cat")
        self.assertEqual(removed, "custom_cat")

    def test_summary_and_budget(self):
        self.service.add_transaction("2024-01-10", "income", "salary", 3000000)
        self.service.add_transaction("2024-01-12", "expense", "transport", 20000)
        self.service.add_transaction("2024-01-15", "expense", "food", 45000)
        self.service.add_transaction("2024-01-20", "expense", "living", 150000)

        self.service.set_budget("2024-01", 500000)

        summary = self.service.get_summary("2024-01", top_n=3)
        self.assertEqual(summary.total_income, 3000000)
        self.assertEqual(summary.total_expense, 215000)
        self.assertEqual(summary.balance, 2785000)
        self.assertEqual(summary.budget_amount, 500000)
        self.assertEqual(summary.usage_rate, 43.0)
        self.assertFalse(summary.is_over_budget)
        self.assertEqual(len(summary.category_expenses), 3)
        self.assertEqual(summary.category_expenses[0][0], "living")
        self.assertEqual(summary.category_expenses[0][1], 150000)

    def test_export_and_import_csv(self):
        self.service.add_transaction("2024-01-10", "income", "salary", 3000000, "월급", "job")
        self.service.add_transaction("2024-01-15", "expense", "food", 15000, "점심", "meal")

        csv_path = self.data_dir / "test_export.csv"
        exported_count = self.service.export_csv(str(csv_path), month="2024-01")
        self.assertEqual(exported_count, 2)
        self.assertTrue(csv_path.exists())

        # Test import into a fresh service instance
        new_dir = tempfile.TemporaryDirectory()
        new_service = BudgetService(Path(new_dir.name))
        imported, skipped = new_service.import_csv(str(csv_path))
        self.assertEqual(imported, 2)
        self.assertEqual(skipped, 0)
        new_items = list(new_service.list_transactions())
        self.assertEqual(len(new_items), 2)
        new_dir.cleanup()


if __name__ == "__main__":
    unittest.main()

