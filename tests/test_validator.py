"""Tests for validators."""
import unittest
from budget_app.exceptions import ValidationError
from budget_app.validator import (
    validate_date,
    validate_month,
    validate_type,
    validate_amount,
    validate_category_name,
    parse_tags,
)


class TestValidator(unittest.TestCase):
    def test_validate_date(self):
        self.assertEqual(validate_date("2024-01-15"), "2024-01-15")
        with self.assertRaises(ValidationError):
            validate_date("2024-13-40")
        with self.assertRaises(ValidationError):
            validate_date("invalid-date")

    def test_validate_month(self):
        self.assertEqual(validate_month("2024-01"), "2024-01")
        with self.assertRaises(ValidationError):
            validate_month("2024-15")

    def test_validate_type(self):
        self.assertEqual(validate_type("income"), "income")
        self.assertEqual(validate_type("expense"), "expense")
        self.assertEqual(validate_type("EXPENSE"), "expense")
        with self.assertRaises(ValidationError):
            validate_type("other")

    def test_validate_amount(self):
        self.assertEqual(validate_amount(15000), 15000)
        self.assertEqual(validate_amount("15,000"), 15000)
        self.assertEqual(validate_amount("100"), 100)
        with self.assertRaises(ValidationError):
            validate_amount(0)
        with self.assertRaises(ValidationError):
            validate_amount(-500)
        with self.assertRaises(ValidationError):
            validate_amount("abc")

    def test_validate_category_name(self):
        self.assertEqual(validate_category_name("food"), "food")
        self.assertEqual(validate_category_name("  transport  "), "transport")
        with self.assertRaises(ValidationError):
            validate_category_name("")
        with self.assertRaises(ValidationError):
            validate_category_name("food,drinks")

    def test_parse_tags(self):
        self.assertEqual(parse_tags("tag1, tag2,tag3"), ["tag1", "tag2", "tag3"])
        self.assertEqual(parse_tags(["a", "b"]), ["a", "b"])
        self.assertEqual(parse_tags(""), [])
        self.assertEqual(parse_tags(None), [])


if __name__ == "__main__":
    unittest.main()

