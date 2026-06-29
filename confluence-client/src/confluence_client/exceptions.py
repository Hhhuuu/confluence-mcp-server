"""Исключения клиента Confluence."""


class ConfluenceClientError(Exception):
    """
    Базовое исключение клиента Confluence.

    Используется как общий предок для ошибок авторизации,
    сетевого взаимодействия и неожиданных ответов API.
    """


class ConfluenceAuthenticationError(ConfluenceClientError):
    """Ошибка аутентификации в Confluence."""


class ConfluenceRequestError(ConfluenceClientError):
    """Ошибка выполнения REST-запроса к Confluence."""
