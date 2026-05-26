"""Persist launchpad JSON under local disk or Azure Blob Storage."""

from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Prefix inside container `agentic-launchpad` (avoids clashing with unrelated blobs).
BLOB_PREFIX = "launchpad"
LOCAL_ROOT = Path(__file__).resolve().parent.parent / "data" / "blob_mirror"


class DataStorage(ABC):
    @abstractmethod
    def read_json(self, key: str) -> Optional[dict[str, Any]]:
        ...

    @abstractmethod
    def write_json(self, key: str, payload: dict[str, Any]) -> None:
        ...

    @abstractmethod
    def delete(self, key: str) -> bool:
        ...

    @abstractmethod
    def list_keys(self, prefix: str) -> list[str]:
        ...


def _safe_key(key: str) -> str:
    cleaned = key.replace("\\", "/").strip("/")
    if ".." in cleaned.split("/"):
        raise ValueError(f"Invalid storage key: {key}")
    return cleaned


class LocalDataStorage(DataStorage):
    def __init__(self, root: Path | None = None) -> None:
        self._root = root or LOCAL_ROOT

    def _path(self, key: str) -> Path:
        return self._root / _safe_key(key)

    def read_json(self, key: str) -> Optional[dict[str, Any]]:
        path = self._path(key)
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not read %s: %s", path, exc)
            return None

    def write_json(self, key: str, payload: dict[str, Any]) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def delete(self, key: str) -> bool:
        path = self._path(key)
        if not path.is_file():
            return False
        try:
            path.unlink()
            return True
        except OSError as exc:
            logger.warning("Could not delete %s: %s", path, exc)
            return False

    def list_keys(self, prefix: str) -> list[str]:
        base = self._path(prefix)
        if not base.exists():
            return []
        if base.is_file():
            return [_safe_key(prefix)]
        keys: list[str] = []
        for path in base.rglob("*.json"):
            rel = path.relative_to(self._root).as_posix()
            keys.append(rel)
        return sorted(keys)


class AzureBlobDataStorage(DataStorage):
    def __init__(
        self,
        *,
        account_name: str,
        container_name: str,
        connection_string: str = "",
        account_key: str = "",
    ) -> None:
        from azure.core.exceptions import ResourceNotFoundError
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient

        self._missing = ResourceNotFoundError
        account_url = f"https://{account_name}.blob.core.windows.net"

        if connection_string:
            service = BlobServiceClient.from_connection_string(connection_string)
        elif account_key:
            service = BlobServiceClient(
                account_url=account_url, credential=account_key
            )
        else:
            service = BlobServiceClient(
                account_url=account_url,
                credential=DefaultAzureCredential(),
            )

        self._container = service.get_container_client(container_name)
        self._prefix = BLOB_PREFIX.strip("/")

    def _blob_name(self, key: str) -> str:
        rel = _safe_key(key)
        return f"{self._prefix}/{rel}" if self._prefix else rel

    def read_json(self, key: str) -> Optional[dict[str, Any]]:
        blob = self._container.get_blob_client(self._blob_name(key))
        try:
            raw = blob.download_blob().readall().decode("utf-8")
            return json.loads(raw)
        except self._missing:
            return None
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read blob %s: %s", key, exc)
            return None

    def write_json(self, key: str, payload: dict[str, Any]) -> None:
        blob = self._container.get_blob_client(self._blob_name(key))
        body = json.dumps(payload, indent=2)
        blob.upload_blob(body, overwrite=True)

    def delete(self, key: str) -> bool:
        blob = self._container.get_blob_client(self._blob_name(key))
        try:
            blob.delete_blob()
            return True
        except self._missing:
            return False
        except OSError as exc:
            logger.warning("Could not delete blob %s: %s", key, exc)
            return False

    def list_keys(self, prefix: str) -> list[str]:
        blob_prefix = self._blob_name(prefix).rstrip("/") + "/"
        keys: list[str] = []
        for item in self._container.list_blobs(name_starts_with=blob_prefix):
            name = item.name
            if not name.endswith(".json"):
                continue
            if self._prefix and name.startswith(f"{self._prefix}/"):
                name = name[len(self._prefix) + 1 :]
            keys.append(name)
        return sorted(keys)


_storage: DataStorage | None = None


def blob_storage_configured() -> bool:
    backend = os.getenv("DATA_STORAGE_BACKEND", "auto").strip().lower()
    if backend == "local":
        return False
    account = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "").strip()
    conn = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip()
    if backend == "blob":
        return bool(conn or account)
    return bool(conn or account)


def get_data_storage() -> DataStorage:
    global _storage
    if _storage is not None:
        return _storage

    if blob_storage_configured():
        account = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "affineblog").strip()
        container = os.getenv(
            "AZURE_STORAGE_CONTAINER_NAME", "agentic-launchpad"
        ).strip()
        _storage = AzureBlobDataStorage(
            account_name=account,
            container_name=container,
            connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING", "").strip(),
            account_key=os.getenv("AZURE_STORAGE_ACCOUNT_KEY", "").strip(),
        )
        logger.info(
            "Data storage: Azure Blob account=%s container=%s prefix=%s",
            account,
            container,
            BLOB_PREFIX,
        )
    else:
        _storage = LocalDataStorage()
        logger.info("Data storage: local mirror at %s", LOCAL_ROOT)
    return _storage


def storage_backend_name() -> str:
    return "azure_blob" if blob_storage_configured() else "local"


def get_storage_status() -> dict[str, str | bool | int]:
    """Summary for /health and startup logs."""
    if not blob_storage_configured():
        return {
            "backend": "local",
            "path": str(LOCAL_ROOT),
            "reachable": LOCAL_ROOT.exists(),
        }
    account = os.getenv("AZURE_STORAGE_ACCOUNT_NAME", "affineblog").strip()
    container = os.getenv(
        "AZURE_STORAGE_CONTAINER_NAME", "agentic-launchpad"
    ).strip()
    status: dict[str, str | bool | int] = {
        "backend": "azure_blob",
        "account": account,
        "container": container,
        "prefix": BLOB_PREFIX,
        "reachable": False,
    }
    try:
        storage = get_data_storage()
        keys = storage.list_keys("sessions")
        status["reachable"] = True
        status["session_blob_count"] = len(
            [k for k in keys if k.startswith("sessions/") and k.endswith(".json")]
        )
    except Exception as exc:
        status["error"] = str(exc)[:200]
        logger.warning("Azure Blob storage check failed: %s", exc)
    return status


def reset_data_storage_for_tests() -> None:
    global _storage
    _storage = None
