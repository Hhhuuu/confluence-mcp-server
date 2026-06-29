"""REST-клиент для работы с Confluence."""

from __future__ import annotations

from dataclasses import dataclass
import mimetypes
from pathlib import Path
from typing import Any, Dict, Optional, Union

import httpx

from .exceptions import (
    ConfluenceAuthenticationError,
    ConfluenceRequestError,
)
from .models import (
    AncestorRef,
    AttachmentSummary,
    AttachmentsResponse,
    BodyValue,
    ConfluencePageResponse,
    CreatePageRequest,
    CurrentUserResponse,
    PageData,
    PageSummary,
    PagesResponse,
    SpaceDetails,
    SpaceRef,
    StorageValue,
    UpdatePageRequest,
    UserInfo,
    VersionInfo,
)

_REST_API = "/rest/api/content"
_CURRENT_USER_API = "/rest/api/user/current"
_SPACE_API = "/rest/api/space"
_VIEW_PAGE_PATH = "/wiki/pages/viewpage.action?pageId="
_ATTACHMENT_API_SUFFIX = "/child/attachment"
_CHILD_PAGE_API_SUFFIX = "/child/page"


@dataclass(frozen=True)
class ConfluenceClientConfig:
    """
    Конфигурация клиента Confluence.

    Attributes:
        base_url: Базовый URL Confluence.
        deployment: Тип развертывания. `cloud` использует префикс `/wiki`,
            `server` работает без него.
        auth_type: Тип авторизации. `basic` использует `username/password`,
            `api_token` использует либо `username/api_token`, либо Bearer token,
            если `username` не задан.
        username: Имя пользователя или email.
        password: Пароль для basic auth.
        api_token: API token или personal access token.
        verify_ssl: Нужно ли проверять SSL-сертификат.
        timeout_seconds: Таймаут HTTP-запросов в секундах.
    """

    base_url: str
    deployment: str = "cloud"
    auth_type: str = "basic"
    username: Optional[str] = None
    password: Optional[str] = None
    api_token: Optional[str] = None
    verify_ssl: bool = True
    timeout_seconds: float = 120.0


class ConfluenceClient:
    """
    Клиент для работы с Confluence REST API.

    Класс изолирует сетевое взаимодействие и предоставляет
    методы, удобные для сервисного слоя page creator.
    """

    def __init__(self, config: ConfluenceClientConfig) -> None:
        """
        Создать клиент Confluence.

        Args:
            config: Параметры подключения и аутентификации.
        """

        self._config = config
        self._api_prefix = "/wiki" if config.deployment == "cloud" else ""
        headers = self._build_headers()
        auth = self._build_auth()
        self._client = httpx.Client(
            base_url=config.base_url.rstrip("/"),
            auth=auth,
            headers=headers,
            verify=config.verify_ssl,
            timeout=config.timeout_seconds,
        )

    def current_user(self) -> UserInfo:
        """
        Получить информацию о текущем пользователе.

        Returns:
            Данные пользователя, под которым выполняются запросы.

        Raises:
            ConfluenceAuthenticationError: Если авторизация неуспешна.
            ConfluenceRequestError: Если API вернул неожиданный ответ.
        """

        response = self._request("GET", self._api_path(_CURRENT_USER_API))
        payload = CurrentUserResponse.model_validate(response.json())
        return UserInfo(
            account_id=payload.account_id,
            display_name=payload.display_name,
            public_name=payload.public_name,
            username=payload.username,
        )

    def get_space(self, space_key: str) -> SpaceDetails:
        """
        Получить информацию о пространстве Confluence.

        Args:
            space_key: Ключ пространства Confluence.

        Returns:
            Данные пространства, включая домашнюю страницу при наличии.
        """

        response = self._request(
            "GET",
            self._api_path(f"{_SPACE_API}/{space_key}"),
            params={"expand": "homepage"},
        )
        return SpaceDetails.model_validate(response.json())

    def find_page(self, title: str, space_key: str) -> PagesResponse:
        """
        Найти страницу по названию в указанном пространстве.

        Args:
            title: Заголовок страницы.
            space_key: Ключ пространства Confluence.

        Returns:
            Ответ со списком найденных страниц.
        """

        response = self._request(
            "GET",
            self._api_path(_REST_API),
            params={"title": title, "spaceKey": space_key, "expand": "version"},
        )
        return PagesResponse.model_validate(response.json())

    def find_page_with_limit(self, space_key: str, limit: int) -> PagesResponse:
        """
        Найти страницы в пространстве с ограничением по размеру выборки.

        Args:
            space_key: Ключ пространства Confluence.
            limit: Ограничение числа возвращаемых записей.

        Returns:
            Ответ Confluence со списком страниц.
        """

        response = self._request(
            "GET",
            self._api_path(_REST_API),
            params={"spaceKey": space_key, "expand": "version", "limit": str(limit)},
        )
        return PagesResponse.model_validate(response.json())

    def find_page_by_id(self, page_id: str) -> PageSummary:
        """
        Найти страницу по идентификатору.

        Args:
            page_id: Идентификатор страницы.

        Returns:
            Поля найденной страницы.
        """

        response = self._request("GET", self._api_path(f"{_REST_API}/{page_id}"))
        return PageSummary.model_validate(response.json())

    def find_page_by_id_with_storage(self, page_id: str) -> PageSummary:
        """
        Найти страницу по идентификатору вместе с телом и пространством.

        Args:
            page_id: Идентификатор страницы.

        Returns:
            Поля найденной страницы с `body.storage`, `version` и `space`.
        """

        response = self._request(
            "GET",
            self._api_path(f"{_REST_API}/{page_id}"),
            params={"expand": "body.storage,version,space"},
        )
        return PageSummary.model_validate(response.json())

    def list_child_pages(
        self,
        page_id: str,
        *,
        include_storage: bool = False,
        start: int = 0,
        limit: int = 100,
    ) -> PagesResponse:
        """
        Получить дочерние страницы для указанной страницы.

        Args:
            page_id: Идентификатор родительской страницы.
            include_storage: Нужно ли раскрывать `body.storage`.
            start: Смещение пагинации.
            limit: Максимум записей в одном запросе.

        Returns:
            Страница результатов Confluence со списком дочерних страниц.
        """

        expand_parts = ["version", "space"]
        if include_storage:
            expand_parts.insert(0, "body.storage")

        response = self._request(
            "GET",
            self._api_path(f"{_REST_API}/{page_id}{_CHILD_PAGE_API_SUFFIX}"),
            params={
                "expand": ",".join(expand_parts),
                "start": str(start),
                "limit": str(limit),
            },
        )
        return PagesResponse.model_validate(response.json())

    def find_attachment_by_filename(
        self,
        page_id: str,
        filename: str,
    ) -> Optional[AttachmentSummary]:
        """
        Найти вложение страницы по имени файла.

        Args:
            page_id: Идентификатор страницы.
            filename: Имя файла вложения.

        Returns:
            Первое найденное вложение или `None`.
        """

        response = self._request(
            "GET",
            self._api_path(f"{_REST_API}/{page_id}{_ATTACHMENT_API_SUFFIX}"),
            params={"filename": filename, "expand": "version"},
        )
        payload = AttachmentsResponse.model_validate(response.json())
        return payload.results[0] if payload.results else None

    def upload_attachment(
        self,
        page_id: str,
        file_path: str | Path,
        *,
        comment: Optional[str] = None,
    ) -> AttachmentSummary:
        """
        Загрузить новое вложение на страницу Confluence.

        Args:
            page_id: Идентификатор страницы.
            file_path: Путь до файла на локальном диске.
            comment: Необязательный комментарий к вложению.

        Returns:
            Краткие данные загруженного вложения.
        """

        path = Path(file_path).expanduser()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data: Dict[str, str] = {"minorEdit": "true"}
        if comment:
            data["comment"] = comment

        with path.open("rb") as stream:
            response = self._request(
                "POST",
                self._api_path(f"{_REST_API}/{page_id}{_ATTACHMENT_API_SUFFIX}"),
                headers={"X-Atlassian-Token": "nocheck"},
                files={"file": (path.name, stream, content_type)},
                data=data,
            )

        payload = AttachmentsResponse.model_validate(response.json())
        if not payload.results:
            raise ConfluenceRequestError(
                f"Confluence не вернул данных о загруженном вложении {path.name}."
            )
        return payload.results[0]

    def update_attachment(
        self,
        page_id: str,
        attachment_id: str,
        file_path: str | Path,
        *,
        comment: Optional[str] = None,
    ) -> AttachmentSummary:
        """
        Обновить бинарные данные уже существующего вложения.

        Args:
            page_id: Идентификатор страницы.
            attachment_id: Идентификатор вложения.
            file_path: Путь до нового файла.
            comment: Необязательный комментарий к новой версии вложения.

        Returns:
            Краткие данные обновленного вложения.
        """

        path = Path(file_path).expanduser()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data: Dict[str, str] = {"minorEdit": "true"}
        if comment:
            data["comment"] = comment

        with path.open("rb") as stream:
            response = self._request(
                "POST",
                self._api_path(
                    f"{_REST_API}/{page_id}{_ATTACHMENT_API_SUFFIX}/{attachment_id}/data"
                ),
                headers={"X-Atlassian-Token": "nocheck"},
                files={"file": (path.name, stream, content_type)},
                data=data,
            )

        payload = AttachmentsResponse.model_validate(response.json())
        if not payload.results:
            raise ConfluenceRequestError(
                f"Confluence не вернул данных об обновленном вложении {path.name}."
            )
        return payload.results[0]

    def upsert_attachment(
        self,
        page_id: str,
        file_path: str | Path,
        *,
        comment: Optional[str] = None,
    ) -> tuple[str, AttachmentSummary]:
        """
        Создать вложение или обновить его, если файл с таким именем уже существует.

        Args:
            page_id: Идентификатор страницы.
            file_path: Путь до файла на диске.
            comment: Необязательный комментарий к вложению.

        Returns:
            Кортеж из действия (`created` или `updated`) и данных вложения.
        """

        path = Path(file_path).expanduser()
        existing = self.find_attachment_by_filename(page_id, path.name)
        if existing is None:
            return "created", self.upload_attachment(page_id, path, comment=comment)
        return "updated", self.update_attachment(page_id, existing.id, path, comment=comment)

    def create_child_page(
        self,
        title: str,
        space_key: str,
        parent_id: Union[int, str],
        content: str,
    ) -> PageData:
        """
        Создать дочернюю страницу.

        Args:
            title: Заголовок новой страницы.
            space_key: Ключ пространства Confluence.
            parent_id: Идентификатор родительской страницы.
            content: Содержимое страницы в формате storage.

        Returns:
            Краткие данные созданной страницы.
        """

        payload = CreatePageRequest(
            title=title,
            space=SpaceRef(key=space_key),
            ancestors=[AncestorRef(id=parent_id)],
            body=BodyValue(storage=StorageValue(value=content)),
        )
        response = self._request(
            "POST",
            self._api_path(_REST_API),
            json=payload.model_dump(mode="json"),
        )
        result = ConfluencePageResponse.model_validate(response.json())
        return self._to_page_data(result)

    def update_page(
        self,
        title: str,
        space_key: str,
        page_id: str,
        version_number: int,
        content: str,
    ) -> PageData:
        """
        Обновить содержимое существующей страницы.

        Args:
            title: Заголовок страницы.
            space_key: Ключ пространства Confluence.
            page_id: Идентификатор страницы.
            version_number: Следующая версия страницы.
            content: Новое содержимое в формате storage.

        Returns:
            Краткие данные обновленной страницы.
        """

        payload = UpdatePageRequest(
            id=page_id,
            title=title,
            space=SpaceRef(key=space_key),
            version=VersionInfo(number=version_number),
            body=BodyValue(storage=StorageValue(value=content)),
        )
        response = self._request(
            "PUT",
            self._api_path(f"{_REST_API}/{page_id}"),
            json=payload.model_dump(mode="json"),
        )
        result = ConfluencePageResponse.model_validate(response.json())
        return self._to_page_data(result)

    def close(self) -> None:
        """
        Закрыть внутренний HTTP-клиент.
        """

        self._client.close()

    def __enter__(self) -> "ConfluenceClient":
        """Открыть клиент для использования в контекстном менеджере."""

        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        """Закрыть клиент после выхода из контекстного менеджера."""

        self.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            response = self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise ConfluenceRequestError(f"Ошибка HTTP при обращении к Confluence: {exc}") from exc

        if response.status_code == 401:
            raise ConfluenceAuthenticationError(
                "Авторизация в Confluence неуспешна. Проверьте логин и пароль."
            )
        if response.status_code >= 400:
            raise ConfluenceRequestError(
                f"Confluence вернул ошибку {response.status_code}: {response.text}"
            )
        return response

    def _to_page_data(self, response: ConfluencePageResponse) -> PageData:
        return PageData(
            title=response.title,
            page_id=response.id,
            page_url=f"{self._config.base_url.rstrip('/')}{self._view_page_path()}{response.id}",
        )

    def _api_path(self, path: str) -> str:
        normalized = path if path.startswith("/") else f"/{path}"
        return f"{self._api_prefix}{normalized}"

    def _view_page_path(self) -> str:
        if self._config.deployment == "cloud":
            return "/wiki/pages/viewpage.action?pageId="
        return "/pages/viewpage.action?pageId="

    def _build_auth(self) -> Optional[httpx.BasicAuth]:
        if self._config.auth_type == "basic":
            if not self._config.username or not self._config.password:
                raise ValueError("Для basic auth нужны username и password.")
            return httpx.BasicAuth(self._config.username, self._config.password)

        if self._config.auth_type == "api_token" and self._config.username:
            return httpx.BasicAuth(self._config.username, self._config.api_token or "")

        return None

    def _build_headers(self) -> Dict[str, str]:
        if self._config.auth_type == "api_token" and not self._config.username:
            if not self._config.api_token:
                raise ValueError("Для api_token auth нужен api_token.")
            return {"Authorization": f"Bearer {self._config.api_token}"}
        return {}
