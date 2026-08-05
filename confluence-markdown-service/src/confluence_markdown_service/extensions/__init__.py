"""Плагины и registry для расширения markdown bridge."""

from .admonitions import AdmonitionsExtension
from .base import (
    ConfluenceMarkdownExtension,
    ExtensionInfo,
    MarkdownImportTransformResult,
    MarkdownRenderResult,
)
from .code_blocks import CodeBlocksExtension
from .date_element import DateElementExtension
from .jira_links import JiraLinksExtension
from .mermaid_diagrams import GeneratedMermaidAttachment, MermaidDiagramsExtension
from .registry import (
    MarkdownExtensionRegistry,
    build_markdown_extension_registry,
    list_builtin_markdown_extensions,
)
from .status_element import StatusElementExtension
from .toc import TocExtension

__all__ = [
    "AdmonitionsExtension",
    "CodeBlocksExtension",
    "DateElementExtension",
    "JiraLinksExtension",
    "GeneratedMermaidAttachment",
    "MermaidDiagramsExtension",
    "ConfluenceMarkdownExtension",
    "ExtensionInfo",
    "MarkdownExtensionRegistry",
    "MarkdownImportTransformResult",
    "MarkdownRenderResult",
    "StatusElementExtension",
    "TocExtension",
    "build_markdown_extension_registry",
    "list_builtin_markdown_extensions",
]
