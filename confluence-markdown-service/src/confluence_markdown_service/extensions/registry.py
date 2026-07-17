"""Registry для расширений markdown bridge."""

from __future__ import annotations

from typing import Iterable, List, Sequence

from ..exceptions import MarkdownBridgeError
from .admonitions import AdmonitionsExtension
from .base import ConfluenceMarkdownExtension, ExtensionInfo
from .code_blocks import CodeBlocksExtension
from .date_element import DateElementExtension
from .jira_links import JiraLinksExtension
from .status_element import StatusElementExtension
from .toc import TocExtension

_BUILTIN_EXTENSION_TYPES = {
    TocExtension.name: TocExtension,
    AdmonitionsExtension.name: AdmonitionsExtension,
    CodeBlocksExtension.name: CodeBlocksExtension,
    DateElementExtension.name: DateElementExtension,
    JiraLinksExtension.name: JiraLinksExtension,
    StatusElementExtension.name: StatusElementExtension,
}

_DEFAULT_BUILTIN_EXTENSION_NAMES = list(_BUILTIN_EXTENSION_TYPES.keys())


class MarkdownExtensionRegistry:
    """Набор активных расширений markdown bridge."""

    def __init__(self, extensions: Sequence[ConfluenceMarkdownExtension] | None = None) -> None:
        self._extensions: List[ConfluenceMarkdownExtension] = list(extensions or [])

    @property
    def extensions(self) -> List[ConfluenceMarkdownExtension]:
        return list(self._extensions)

    @property
    def names(self) -> List[str]:
        return [extension.name for extension in self._extensions]

    def preprocess_markdown(self, markdown_text: str) -> str:
        prepared = markdown_text
        for extension in self._extensions:
            prepared = extension.preprocess_markdown(prepared)
        return prepared

    @classmethod
    def builtin_infos(cls) -> List[ExtensionInfo]:
        return [
            ExtensionInfo(name=name, description=extension_type.description)
            for name, extension_type in _BUILTIN_EXTENSION_TYPES.items()
        ]

    @classmethod
    def build(
        cls,
        enabled_extensions: Sequence[str] | None = None,
        extra_extensions: Sequence[ConfluenceMarkdownExtension] | None = None,
    ) -> "MarkdownExtensionRegistry":
        extensions: list[ConfluenceMarkdownExtension] = []
        builtin_names = _DEFAULT_BUILTIN_EXTENSION_NAMES if enabled_extensions is None else list(enabled_extensions)
        for name in builtin_names:
            extension_type = _BUILTIN_EXTENSION_TYPES.get(name)
            if extension_type is None:
                supported = ", ".join(sorted(_BUILTIN_EXTENSION_TYPES))
                raise MarkdownBridgeError(
                    f"Неизвестное markdown-расширение '{name}'. "
                    f"Поддерживаются: {supported}."
                )
            extensions.append(extension_type())

        for extension in extra_extensions or []:
            extensions.append(extension)

        return cls(extensions=extensions)


def list_builtin_markdown_extensions() -> List[ExtensionInfo]:
    """Вернуть список встроенных расширений markdown bridge."""

    return MarkdownExtensionRegistry.builtin_infos()


def build_markdown_extension_registry(
    enabled_extensions: Sequence[str] | None = None,
    extra_extensions: Sequence[ConfluenceMarkdownExtension] | None = None,
) -> MarkdownExtensionRegistry:
    """Построить registry по именам встроенных и пользовательским расширениям."""

    return MarkdownExtensionRegistry.build(
        enabled_extensions=enabled_extensions,
        extra_extensions=extra_extensions,
    )
