"""Тесты proofread helpers."""

from __future__ import annotations

import unittest

from confluence_mcp.proofread import (
    build_comment_body_storage,
    markdown_to_plain_text,
    suggestion_from_languagetool_match,
)


class ProofreadHelperTests(unittest.TestCase):
    def test_markdown_to_plain_text_removes_markdown_noise(self) -> None:
        text = markdown_to_plain_text("# Заголовок\n\nЭто [слово](https://example.test) и `code`.")

        self.assertIn("Заголовок", text)
        self.assertIn("Это слово", text)
        self.assertNotIn("https://example.test", text)
        self.assertNotIn("code", text)

    def test_suggestion_counts_text_selection_occurrence(self) -> None:
        text = "Ошибка тут. Ошибка здесь."
        offset = text.rfind("Ошибка")
        match = {
            "offset": offset,
            "length": len("Ошибка"),
            "message": "Возможная ошибка.",
            "replacements": [{"value": "Правка"}],
            "rule": {"id": "TEST_RULE"},
        }

        suggestion = suggestion_from_languagetool_match(text, match)

        self.assertIsNotNone(suggestion)
        assert suggestion is not None
        self.assertEqual(suggestion.text_selection, "Ошибка")
        self.assertEqual(suggestion.text_selection_match_count, 2)
        self.assertEqual(suggestion.text_selection_match_index, 1)
        self.assertIn("Правка", suggestion.comment_body_storage)

    def test_comment_body_escapes_html(self) -> None:
        body = build_comment_body_storage(
            message="Исправить <тег>",
            text_selection="<ошибка>",
            replacements=["<правка>"],
            rule_id="RULE",
        )

        self.assertIn("&lt;тег&gt;", body)
        self.assertIn("&lt;ошибка&gt;", body)
        self.assertIn("&lt;правка&gt;", body)


if __name__ == "__main__":
    unittest.main()
