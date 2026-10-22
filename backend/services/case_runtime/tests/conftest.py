"""Real signatures, owned verifier HTTP mock; no identity dependency overrides."""

from datetime import datetime, timezone
import json, time
from types import SimpleNamespace
from uuid import uuid4
import httpx, jwt, pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from app.main import create_app
from app.config import Settings
from sg_core import iam_verification as verifier
from sg_core.user_principals import UserClientBinding

A = "11111111-1111-4111-8111-111111111111"
B = "22222222-2222-4222-8222-222222222222"
ISSUER = "https://identity.internal.test/realms/synthetic"
HTTP_CLIENT = httpx.Client


@pytest.fixture(scope="module")
def key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture
def api(monkeypatch, key):
    binding = UserClientBinding(
        issuer=ISSUER,
        client_id="review-browser",
        tenant_id=A,
        contract="keycloak-user-v1",
        service_accounts_enabled=False,
        token_exchange_enabled=False,
    )
    config = Settings(
        _env_file=None,
        ENVIRONMENT="test",
        IAM_AGENT_URL="https://iam.internal.test",
        KEYCLOAK_CLIENT_ID="review-audience",
        IAM_USER_CLIENT_BINDINGS=(binding,),
    )
    app = create_app(config)
    state = SimpleNamespace(
        app=app, calls=[], unavailable=False, key=key, config=config
    )

    def sign(subject=None, **update):
        claims = dict(
            sub=subject or str(uuid4()),
            tenant_id=A,
            iss=ISSUER,
            aud="review-audience",
            azp="review-browser",
            typ="Bearer",
            sg_principal_type="user",
            sg_identity_contract="keycloak-user-v1",
            realm_access={"roles": ["SOC_ANALYST"]},
            exp=int(time.time()) + 600,
            iat=int(time.time()) - 1,
        )
        return jwt.encode(
            {**claims, **update}, key, algorithm="RS256", headers={"kid": "review-key"}
        )

    state.sign = sign
    state.headers = lambda subject=None, **update: {
        "Authorization": "Bearer " + sign(subject, **update)
    }

    def transport(request):
        state.calls.append(request)
        assert (
            str(request.url)
            == "https://iam.internal.test/internal/iam/auth/validate-token"
        )
        if state.unavailable:
            raise httpx.ConnectError("Synthetic IAM outage")
        try:
            p = jwt.decode(
                json.loads(request.content)["token"],
                key.public_key(),
                algorithms=["RS256"],
                issuer=ISSUER,
                audience="review-audience",
            )
        except jwt.PyJWTError:
            return httpx.Response(200, json={"valid": False})
        return httpx.Response(
            200,
            json=dict(
                valid=True,
                payload=p,
                tenant_id=p["tenant_id"],
                user_id=p["sub"],
                roles=p["realm_access"]["roles"],
                expires_at=datetime.fromtimestamp(p["exp"], timezone.utc).isoformat(),
            ),
        )

    monkeypatch.setattr(
        verifier.httpx,
        "Client",
        lambda **kwargs: HTTP_CLIENT(
            transport=httpx.MockTransport(transport), **kwargs
        ),
    )
    with TestClient(app) as client:
        state.client = client
        yield state
    assert not app.dependency_overrides
