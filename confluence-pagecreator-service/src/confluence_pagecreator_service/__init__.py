"""Сервисный слой создания страниц."""

from .config import AppConfig, ConfluenceAppConfig, load_app_config
from .dto import CreatePagesRequest, CreatePagesResult, PlannedPage
from .exceptions import (
    DuplicateTitleError,
    ConfigFileNotFoundError,
    InvalidConfigError,
    InvalidPathError,
    InvalidSecretsError,
    PageCreatorServiceError,
    SecretsFileNotFoundError,
)
from .models import CreationPlan, CreationPlanItem, LevelNode, ParsedPath
from .path_parser import parse_path, parse_paths
from .planner import build_creation_plan, build_level_index, render_plan_structure
from .secrets import ConfluenceSecrets, SecretStore, load_secrets, load_secrets_from_env
from .service import PageCreatorService

__all__ = [
    "AppConfig",
    "ConfigFileNotFoundError",
    "ConfluenceAppConfig",
    "ConfluenceSecrets",
    "CreationPlan",
    "CreationPlanItem",
    "CreatePagesRequest",
    "CreatePagesResult",
    "DuplicateTitleError",
    "InvalidConfigError",
    "InvalidPathError",
    "InvalidSecretsError",
    "LevelNode",
    "PageCreatorService",
    "PageCreatorServiceError",
    "ParsedPath",
    "PlannedPage",
    "SecretStore",
    "SecretsFileNotFoundError",
    "build_creation_plan",
    "build_level_index",
    "load_app_config",
    "load_secrets",
    "load_secrets_from_env",
    "parse_path",
    "parse_paths",
    "render_plan_structure",
]
