"""Limiter ownership/failure tests plus an opt-in actual shared Redis test."""

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import os
import secrets

from fastapi import HTTPException
import pytest

from app.core.rate_limit import RateLimitPolicy, RedisBudgetStore, peer_address


def scope(peer, *headers):
    return {"client": (peer, 1), "headers": list(headers)}


def test_forwarded_headers_from_untrusted_peer_do_not_select_bucket():
    policy = RateLimitPolicy()
    assert (
        peer_address(
            scope(
                "192.0.2.1",
                (b"x-forwarded-for", b"198.51.100.1"),
                (b"x-tenant-id", b"forged"),
            ),
            policy,
        )
        == "192.0.2.1"
    )


def test_trusted_chain_is_validated_before_selection():
    policy = RateLimitPolicy(trusted_proxy_cidrs=("10.0.0.0/24",))
    assert (
        peer_address(
            scope(
                "10.0.0.2", (b"x-forwarded-for", b"192.0.2.1, 198.51.100.1, 10.0.0.3")
            ),
            policy,
        )
        == "198.51.100.1"
    )
    for values in [(b"bad, 198.51.100.1",), (b"198.51.100.1", b"198.51.100.1"), (b"",)]:
        with pytest.raises(HTTPException) as error:
            peer_address(
                scope("10.0.0.2", *((b"x-forwarded-for", v) for v in values)), policy
            )
        assert error.value.status_code == 400


@pytest.mark.parametrize(
    "kwargs",
    [
        {"namespace": "*"},
        {"trusted_proxy_cidrs": ("0.0.0.0/0",)},
        {"redis_url": "redis://owned/0?socket_timeout=999"},
        {"peer_rpm": 0},
    ],
)
def test_invalid_owned_policy_is_rejected(kwargs):
    with pytest.raises(ValueError):
        RateLimitPolicy(**kwargs)


class RedisReply:
    def __init__(self):
        self.reply = [1, 30]
        self.calls = []

    def eval(self, *args):
        self.calls.append(args)
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def test_unavailability_fail_closed_and_next_request_recovery():
    client = RedisReply()
    store = RedisBudgetStore(RateLimitPolicy(), client)
    client.reply = ConnectionError("sensitive endpoint")
    with pytest.raises(HTTPException) as error:
        store.check((("peer", "192.0.2.1", 1),))
    assert error.value.status_code == 503 and "sensitive" not in error.value.detail
    client.reply = [1, 30]
    store.check((("peer", "192.0.2.1", 1),))
    assert len(client.calls) == 2


def test_explicit_fail_open_and_limit_status_are_distinct():
    client = RedisReply()
    store = RedisBudgetStore(RateLimitPolicy(fail_closed=False), client)
    client.reply = ConnectionError()
    store.check((("peer", "192.0.2.1", 1),))
    client.reply = [0, 12]
    with pytest.raises(HTTPException) as error:
        store.check((("peer", "192.0.2.1", 1),))
    assert error.value.status_code == 429 and error.value.headers == {
        "Retry-After": "12"
    }


def test_verified_subject_and_tenant_are_stable_buckets():
    client = RedisReply()
    store = RedisBudgetStore(RateLimitPolicy(), client)
    store.check_identity(SimpleNamespace(tenant_id="owned", user_id="actor"))
    first = client.calls[-1]
    store.check_identity(SimpleNamespace(tenant_id="owned", user_id="actor"))
    assert first == client.calls[-1] and first[1] == 2
    assert "owned" not in str(first[2:4]) and "actor" not in str(first[2:4])
    store.check_identity(SimpleNamespace(tenant_id="foreign", user_id="actor"))
    assert first[2:4] != client.calls[-1][2:4]


@pytest.mark.skipif(
    not os.getenv("SG_TEST_REDIS_SOCKET"),
    reason="Actual isolated Redis Unix socket required",
)
def test_actual_redis_two_clients_atomic_budget_no_partial_spend():
    import redis

    client = redis.Redis(
        unix_socket_path=os.environ["SG_TEST_REDIS_SOCKET"], socket_timeout=1
    )
    other = redis.Redis(
        unix_socket_path=os.environ["SG_TEST_REDIS_SOCKET"], socket_timeout=1
    )
    policy = RateLimitPolicy(namespace="task7-" + secrets.token_hex(8))
    stores = [RedisBudgetStore(policy, client), RedisBudgetStore(policy, other)]

    def check(i):
        try:
            stores[i % 2].check((("tenant", "synthetic", 7), ("subject", "actor", 7)))
            return True
        except HTTPException as exc:
            assert exc.status_code == 429
            return False

    try:
        # Thirty independent requests through two clients share seven grants.
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(check, range(30)))
        assert sum(results) == 7
        keys = list(client.scan_iter(match=policy.namespace + ":*"))
        assert len(keys) == 2 and {int(client.get(k)) for k in keys} == {7}
        assert all(0 < client.ttl(k) <= 61 for k in keys)
        # A denied second bucket must not spend an otherwise unused first one.
        with pytest.raises(HTTPException):
            stores[0].check((("tenant", "different", 7), ("subject", "actor", 7)))
        assert len(list(client.scan_iter(match=policy.namespace + ":*"))) == 2
    finally:
        for key in client.scan_iter(match=policy.namespace + ":*"):
            client.delete(key)
        client.close()
        other.close()
