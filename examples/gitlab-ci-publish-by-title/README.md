# Публикация Markdown из GitLab CI

Пример обновляет существующую страницу Confluence по ключу пространства и
точному заголовку. MCP- и HTTP-серверы не запускаются: job использует напрямую
`confluence-client` и `confluence-markdown-service`.

## Подготовка

Добавьте в GitLab через **Settings -> CI/CD -> Variables**:

- `CONFLUENCE_BASE_URL` - адрес Confluence Server/Data Center;
- `CONFLUENCE_API_TOKEN` - Personal Access Token, с флагами Masked и Protected;
- при basic-аутентификации вместо токена задайте `CONFLUENCE_AUTH_TYPE=basic`,
  `CONFLUENCE_USERNAME` и `CONFLUENCE_PASSWORD`.

Остальные параметры можно оставить в `.gitlab-ci.yml`:

- `CONFLUENCE_SPACE_KEY` - ключ пространства, например `DOC`;
- `CONFLUENCE_PAGE_TITLE` - точный заголовок существующей страницы;
- `MARKDOWN_FILE` - путь к Markdown-файлу относительно корня репозитория;
- `CONFLUENCE_VERIFY_SSL` - проверка сертификата, по умолчанию `true`.

Для bearer-токена Server/Data Center не задавайте `CONFLUENCE_USERNAME`.

## Подключение

Скопируйте содержимое `.gitlab-ci.yml` из примера в pipeline проекта либо
подключите его через `include`. Пути установки предполагают, что каталоги
`confluence-client` и `confluence-markdown-service` доступны в checkout job.

Job выполняет следующие действия:

1. Ищет страницу через REST API по `CONFLUENCE_SPACE_KEY` и
   `CONFLUENCE_PAGE_TITLE`.
2. Проверяет точное совпадение заголовка.
3. Обновляет найденную страницу содержимым `MARKDOWN_FILE`.
4. Загружает локальные файлы и Mermaid attachment, если они используются в
   Markdown.

Если страница не найдена или найдено несколько совпадений, job завершается с
ошибкой и ничего не создаёт.

Для внутреннего Confluence с недоверенным сертификатом временно можно задать
`CONFLUENCE_VERIFY_SSL=false`. Для постоянной эксплуатации предпочтительно
добавить корпоративный CA в образ runner.
