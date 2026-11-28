"""Catalog title validation and backwards compatibility without database access."""
import unittest

from app.catalog_transfer import catalog_exercise_title


class CatalogTitleTests(unittest.TestCase):
    def test_source_language_title_is_preserved(self):
        for version in (1, 2):
            with self.subTest(version=version):
                self.assertEqual(
                    catalog_exercise_title({"title": "  সকালের চা  "}, "bn", 1, version),
                    "সকালের চা",
                )

    def test_current_exports_require_valid_titles(self):
        for data in ({}, {"title": None}, {"title": " \t\n"}, {"title": 123}, {"title": "a" * 31}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                catalog_exercise_title(data, "bn", 1, 2)

    def test_maximum_title_length_is_accepted(self):
        self.assertEqual(catalog_exercise_title({"title": "a" * 30}, "en", 1, 2), "a" * 30)

    def test_legacy_placeholders_do_not_reveal_prompts(self):
        data = {"source_text": "PRIVATE_PROMPT_SENTINEL", "preferred_solutions": ["PRIVATE_ANSWER"]}
        for code, expected in (("bn", "অনুশীলন"), ("en", "Exercise"), ("de", "Übung"), ("es", "Ejercicio")):
            with self.subTest(source=code):
                title = catalog_exercise_title(data, code, 9, 1)
                self.assertEqual(title, f"{expected} #9")
                self.assertNotIn("PRIVATE", title)
                self.assertNotEqual(title, catalog_exercise_title(data, code, 10, 1))


if __name__ == "__main__":
    unittest.main()
