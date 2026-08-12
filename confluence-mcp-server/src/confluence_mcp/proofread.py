"""Proofreading helpers for Confluence inline comments."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
import re
from typing import Any, Iterable, List, Optional

import httpx


_DEFAULT_LANGUAGETOOL_URL = "http://127.0.0.1:8010"
_CODE_BLOCK_PATTERN = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_PATTERN = re.compile(r"`[^`]+`")
_IMAGE_PATTERN = re.compile(r"!\[[^\]]*]\([^)]*\)")
_LINK_PATTERN = re.compile(r"\[([^\]]+)]\([^)]*\)")
_MARKDOWN_MARKER_PATTERN = re.compile(r"(^|\n)\s{0,3}(#{1,6}|[-*+] |\d+\. |>)\s*")
_WHITESPACE_PATTERN = re.compile(r"[ \t]+")


@dataclass(frozen=True)
class ProofreadSuggestion:
    """A single proofreading suggestion mapped to a Confluence text selection."""

    message: str
    text_selection: str
    text_selection_match_count: int
    text_selection_match_index: int
    replacements: List[str]
    rule_id: Optional[str]
    context: str
    offset: int
    length: int
    comment_body_storage: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "text_selection": self.text_selection,
            "text_selection_match_count": self.text_selection_match_count,
            "text_selection_match_index": self.text_selection_match_index,
            "replacements": self.replacements,
            "rule_id": self.rule_id,
            "context": self.context,
            "offset": self.offset,
            "length": self.length,
            "comment_body_storage": self.comment_body_storage,
        }


@dataclass(frozen=True)
class ProofreadResult:
    """Result of checking a text with LanguageTool."""

    language: str
    source_text: str
    suggestions: List[ProofreadSuggestion]
    truncated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "language": self.language,
            "suggestions": [suggestion.to_dict() for suggestion in self.suggestions],
            "suggestion_count": len(self.suggestions),
            "truncated": self.truncated,
        }


def markdown_to_plain_text(markdown: str) -> str:
    """Convert exported Markdown to plain text suitable for proofreading."""

    text = _CODE_BLOCK_PATTERN.sub("\n", markdown)
    text = _INLINE_CODE_PATTERN.sub("", text)
    text = _IMAGE_PATTERN.sub("", text)
    text = _LINK_PATTERN.sub(r"\1", text)
    text = _MARKDOWN_MARKER_PATTERN.sub("\n", text)
    text = text.replace("**", "").replace("__", "").replace("*", "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE_PATTERN.sub(" ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def check_text_with_languagetool(
    text: str,
    *,
    language: str = "ru-RU",
    languagetool_url: str = _DEFAULT_LANGUAGETOOL_URL,
    max_suggestions: int = 20,
    timeout_seconds: float = 30.0,
) -> ProofreadResult:
    """Check text via LanguageTool /v2/check and map matches to text selections."""

    if max_suggestions < 1:
        raise ValueError("max_suggestions должен быть больше 0.")

    normalized_url = languagetool_url.rstrip("/")
    response = httpx.post(
        f"{normalized_url}/v2/check",
        data={"text": text, "language": language},
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    matches = payload.get("matches", [])

    suggestions: list[ProofreadSuggestion] = []
    for match in matches:
        suggestion = suggestion_from_languagetool_match(text, match)
        if suggestion is None:
            continue
        suggestions.append(suggestion)
        if len(suggestions) >= max_suggestions:
            break

    return ProofreadResult(
        language=language,
        source_text=text,
        suggestions=suggestions,
        truncated=len(matches) > len(suggestions),
    )


def suggestion_from_languagetool_match(text: str, match: dict[str, Any]) -> Optional[ProofreadSuggestion]:
    """Build a suggestion from one LanguageTool match."""

    offset = int(match.get("offset", 0))
    length = int(match.get("length", 0))
    if length <= 0 or offset < 0 or offset + length > len(text):
        return None

    text_selection = text[offset : offset + length].strip()
    if not text_selection:
        return None

    occurrences = list(_iter_occurrences(text, text_selection))
    try:
        match_index = occurrences.index(offset)
    except ValueError:
        match_index = sum(1 for occurrence in occurrences if occurrence < offset)

    replacements = [
        str(item.get("value"))
        for item in match.get("replacements", [])[:5]
        if item.get("value")
    ]
    message = str(match.get("message") or "Проверьте этот фрагмент.")
    rule = match.get("rule") or {}
    rule_id = rule.get("id")
    context = (match.get("context") or {}).get("text") or _context_around(text, offset, length)

    return ProofreadSuggestion(
        message=message,
        text_selection=text_selection,
        text_selection_match_count=max(len(occurrences), 1),
        text_selection_match_index=match_index,
        replacements=replacements,
        rule_id=str(rule_id) if rule_id else None,
        context=context,
        offset=offset,
        length=length,
        comment_body_storage=build_comment_body_storage(
            message=message,
            text_selection=text_selection,
            replacements=replacements,
            rule_id=str(rule_id) if rule_id else None,
        ),
    )


def build_comment_body_storage(
    *,
    message: str,
    text_selection: str,
    replacements: Iterable[str],
    rule_id: Optional[str] = None,
) -> str:
    """Render a Confluence storage-format inline comment body."""

    replacement_values = [value for value in replacements if value]
    parts = [
        "<p><strong>Проверка орфографии и пунктуации</strong></p>",
        f"<p>{escape(message)}</p>",
        f"<p>Фрагмент: <code>{escape(text_selection)}</code></p>",
    ]
    if replacement_values:
        parts.append(
            "<p>Варианты: "
            + ", ".join(f"<code>{escape(value)}</code>" for value in replacement_values)
            + "</p>"
        )
    if rule_id:
        parts.append(f"<p>Правило LanguageTool: <code>{escape(rule_id)}</code></p>")
    return "".join(parts)


def _iter_occurrences(text: str, needle: str):
    start = 0
    while True:
        index = text.find(needle, start)
        if index == -1:
            return
        yield index
        start = index + max(len(needle), 1)


def _context_around(text: str, offset: int, length: int, radius: int = 80) -> str:
    start = max(0, offset - radius)
    end = min(len(text), offset + length + radius)
    return text[start:end].strip()
