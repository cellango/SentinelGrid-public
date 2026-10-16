"""Tests for passwordless token store (memory fallback)."""

from datetime import datetime, timedelta

from app.services.passwordless_store import PasswordlessStore


def test_passwordless_store_save_get_consume_memory():
    """Store, read, and consume a token using memory backend."""
    store = PasswordlessStore(prefix="test")
    store.use_redis = False  # force memory for test
    token_hash = "abc123"

    saved = store.save(token_hash, {"foo": "bar"}, ttl_seconds=60)
    assert saved is True

    record = store.get(token_hash)
    assert record is not None
    assert record["foo"] == "bar"

    consumed = store.consume(token_hash)
    assert consumed is not None
    assert consumed["foo"] == "bar"

    assert store.get(token_hash) is None  # single-use


def test_passwordless_store_expired_token():
    """Expired tokens should be purged on access."""
    store = PasswordlessStore(prefix="test")
    store.use_redis = False
    token_hash = "expired123"
    expired_at = (datetime.utcnow() - timedelta(seconds=1)).isoformat()

    store.save(token_hash, {"foo": "bar", "expires_at": expired_at}, ttl_seconds=1)
    assert store.get(token_hash) is None
