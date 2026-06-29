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
    "PageData",
    "PageSummary",
    "PagesResponse",
    "SpaceDetails",
    "UserInfo",
]
