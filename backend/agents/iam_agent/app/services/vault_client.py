"""Lightweight Vault KV v2 client for secrets storage."""

import logging
from typing import Any, Dict, List, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class VaultClient:
    """Minimal Vault KV v2 client using httpx."""

    def __init__(
        self,
        addr: Optional[str] = None,
        token: Optional[str] = None,
        mount: Optional[str] = None,
        namespace: Optional[str] = None,
    ):
        self.addr = (addr or settings.VAULT_ADDR).rstrip("/")
        self.token = token or settings.VAULT_TOKEN
        self.mount = mount or settings.VAULT_MOUNT or "secret"
        self.namespace = namespace or settings.VAULT_NAMESPACE

        if not self.token:
            raise RuntimeError("Vault token not configured")

        self._client = httpx.Client(timeout=10.0, verify=settings.VAULT_VERIFY_TLS)

    def _headers(self) -> Dict[str, str]:
        headers = {"X-Vault-Token": self.token}
        if self.namespace:
            headers["X-Vault-Namespace"] = self.namespace
        return headers

    def _kv_data_path(self, path: str) -> str:
        return f"{self.addr}/v1/{self.mount}/data/{path}"

    def _kv_metadata_path(self, path: str) -> str:
        return f"{self.addr}/v1/{self.mount}/metadata/{path}"

    def write_secret(self, path: str, data: Dict[str, Any]) -> None:
        """Write secret data to KV v2."""
        url = self._kv_data_path(path)
        resp = self._client.post(url, headers=self._headers(), json={"data": data})
        resp.raise_for_status()

    def read_secret(self, path: str) -> Optional[Dict[str, Any]]:
        """Read secret data from KV v2."""
        url = self._kv_data_path(path)
        resp = self._client.get(url, headers=self._headers())
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("data", {}).get("data")

    def delete_secret(self, path: str) -> None:
        """Soft-delete latest version of a secret."""
        url = f"{self.addr}/v1/{self.mount}/delete/{path}"
        resp = self._client.post(url, headers=self._headers())
        resp.raise_for_status()

    def list_secrets(self, path: str) -> List[str]:
        """List keys under a path (KV v2 metadata)."""
        url = self._kv_metadata_path(path)
        resp = self._client.request(
            "LIST",
            url,
            headers=self._headers(),
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("data", {}).get("keys", []) or []
