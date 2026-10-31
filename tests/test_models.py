"""Tests for data models."""
import unittest
from budget_app.models import Transaction, Category, Budget, SummaryResult


class TestModels(unittest.TestCase):
    def test_transaction_dict_conversion(self):
        tx = Transaction(
            id="TX-000001",
            date="2024-01-15",
            type="expense",
            amount=15000,
            category="food",
            memo="점심",
            tags=["meal", "lunch"],
        )
        d = tx.to_dict()
        self.assertEqual(d["id"], "TX-000001")
        self.assertEqual(d["amount"], 15000)

        restored = Transaction.from_dict(d)
        self.assertEqual(restored.id, tx.id)
        self.assertEqual(restored.tags, ["meal", "lunch"])

    def test_category_dict(self):
        cat = Category(name="food")
        self.assertEqual(cat.to_dict(), {"name": "food"})
        restored = Category.from_dict({"name": "transport"})
        self.assertEqual(restored.name, "transport")

    def test_budget_dict(self):
        b = Budget(month="2024-01", amount=500000)
        self.assertEqual(b.to_dict(), {"month": "2024-01", "amount": 500000})
        restored = Budget.from_dict({"month": "2024-02", "amount": 300000})
        self.assertEqual(restored.month, "2024-02")
        self.assertEqual(restored.amount, 300000)

    def test_summary_result_properties(self):
        summary = SummaryResult(
            month="2024-01",
            total_income=3000000,
            total_expense=215000,
            balance=2785000,
            category_expenses=[("rent", 150000), ("food", 65000)],
            budget_amount=500000,
        )
        self.assertEqual(summary.usage_rate, 43.0)
        self.assertFalse(summary.is_over_budget)

        over_summary = SummaryResult(
            month="2024-01",
            total_income=100000,
            total_expense=600000,
            balance=-500000,
            category_expenses=[],
            budget_amount=500000,
        )
        self.assertEqual(over_summary.usage_rate, 120.0)
        self.assertTrue(over_summary.is_over_budget)


if __name__ == "__main__":
    unittest.main()

