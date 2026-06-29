FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY confluence-pagecreator-core /app/confluence-pagecreator-core
COPY confluence-client /app/confluence-client
COPY confluence-pagecreator-service /app/confluence-pagecreator-service
COPY confluence-pagecreator-mcp-server /app/confluence-pagecreator-mcp-server
COPY config /app/config
COPY secrets /app/secrets
COPY .mcp.json /app/.mcp.json
COPY EXTERNAL_CONSUMERS.md /app/EXTERNAL_CONSUMERS.md
COPY README.md /app/README.md

RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir \
        -e /app/confluence-pagecreator-core \
        -e /app/confluence-client \
        -e /app/confluence-pagecreator-service \
        -e /app/confluence-pagecreator-mcp-server

ENV PAGECREATOR_CONFIG_PATH=/app/config/app.yaml
ENV PAGECREATOR_SECRETS_PATH=/app/secrets/confluence.yaml
ENV PAGECREATOR_RUNTIME_MODE=http-api
ENV PAGECREATOR_HTTP_HOST=0.0.0.0
ENV PAGECREATOR_HTTP_PORT=8000
ENV PAGECREATOR_MCP_HOST=0.0.0.0
ENV PAGECREATOR_MCP_PORT=8000

EXPOSE 8000

CMD ["python", "-m", "confluence_pagecreator_mcp.launch"]
