"""Модели данных для работы с Confluence REST API."""

from __future__ import annotations

from typing import List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field


class ConfluenceModel(BaseModel):
    """Базовая модель Confluence API с игнорированием лишних полей."""

    model_config = ConfigDict(extra="ignore")


class SpaceRef(ConfluenceModel):
    """Ссылка на пространство Confluence."""

    key: str


class AncestorRef(ConfluenceModel):
    """Ссылка на родительскую страницу."""

    id: Union[int, str]


class StorageValue(ConfluenceModel):
    """Содержимое страницы в формате storage."""

    value: str
    representation: str = "storage"


class BodyValue(ConfluenceModel):
    """Тело страницы Confluence."""

    storage: StorageValue


class VersionInfo(ConfluenceModel):
    """Информация о версии страницы."""

    number: int


class PageSummary(ConfluenceModel):
    """Краткая информация о странице Confluence."""

    id: str
    status: Optional[str] = None
    title: str
    type: Optional[str] = None
    version: Optional[VersionInfo] = None
    space: Optional[SpaceRef] = None
    body: Optional[BodyValue] = None


class PagesResponse(ConfluenceModel):
    """Ответ API со списком страниц."""

    results: List[PageSummary] = Field(default_factory=list)
    size: Optional[int] = None


class CurrentUserResponse(ConfluenceModel):
    """Ответ API с текущим пользователем."""

    account_id: Optional[str] = Field(default=None, alias="accountId")
    display_name: Optional[str] = Field(default=None, alias="displayName")
    public_name: Optional[str] = Field(default=None, alias="publicName")
    username: Optional[str] = None


class UserInfo(ConfluenceModel):
    """Информация о пользователе."""

    account_id: Optional[str] = None
    display_name: Optional[str] = None
    public_name: Optional[str] = None
    username: Optional[str] = None


class SpaceDetails(ConfluenceModel):
    """Информация о пространстве Confluence."""

    id: Optional[int] = None
    key: str
    name: Optional[str] = None
    type: Optional[str] = None
    homepage: Optional[PageSummary] = None


class ConfluencePageResponse(ConfluenceModel):
    """Ответ API после создания или обновления страницы."""

    id: str
    title: str


class PageData(ConfluenceModel):
    """Краткие данные по странице для сервисного слоя."""

    title: str
    page_id: str
    page_url: str


class CreatePageRequest(ConfluenceModel):
    """Запрос на создание страницы."""

    type: str = "page"
    title: str
    space: SpaceRef
    ancestors: List[AncestorRef]
    body: BodyValue


class UpdatePageRequest(ConfluenceModel):
    """Запрос на обновление страницы."""

    id: str
    type: str = "page"
    title: str
    space: SpaceRef
    version: VersionInfo
    body: BodyValue
