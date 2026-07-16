"""Плагины и registry для расширения markdown bridge."""

from .admonitions import AdmonitionsExtension
from .base import (
    ConfluenceMarkdownExtension,
    ExtensionInfo,
    MarkdownImportTransformResult,
    MarkdownRenderResult,
)
from .code_blocks import CodeBlocksExtension
from .jira_links import JiraLinksExtension
from .registry import (
    MarkdownExtensionRegistry,
    build_markdown_extension_registry,
    list_builtin_markdown_extensions,
)
from .toc import TocExtension

__all__ = [
    "AdmonitionsExtension",
    "CodeBlocksExtension",
    "JiraLinksExtension",
    "ConfluenceMarkdownExtension",
    "ExtensionInfo",
    "MarkdownExtensionRegistry",
    "MarkdownImportTransformResult",
    "MarkdownRenderResult",
    "TocExtension",
    "build_markdown_extension_registry",
    "list_builtin_markdown_extensions",
]
