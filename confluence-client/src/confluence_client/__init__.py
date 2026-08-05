"""Пакет клиента Confluence."""

from .client import ConfluenceClient, ConfluenceClientConfig
from .exceptions import (
    ConfluenceAuthenticationError,
    ConfluenceClientError,
    ConfluenceRequestError,
)
from .models import (
    AttachmentSummary,
    AttachmentsResponse,
    MovePageResult,
    PageData,
    PageSummary,
    PagesResponse,
    SpaceDetails,
    UserInfo,
)

__all__ = [
    "ConfluenceAuthenticationError",
    "ConfluenceClient",
    "ConfluenceClientConfig",
    "ConfluenceClientError",
    "ConfluenceRequestError",
    "AttachmentSummary",
    "AttachmentsResponse",
    "MovePageResult",
    "PageData",
    "PageSummary",
    "PagesResponse",
    "SpaceDetails",
    "UserInfo",
]
