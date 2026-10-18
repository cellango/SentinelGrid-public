# SPDX-License-Identifier: Apache-2.0
"""Opt-in new loopback-only lab. Never points at an existing realm or database."""

import argparse
import atexit
import base64
import datetime
import hashlib
import ipaddress
import json
import os
import secrets
import shutil
import signal
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import httpx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--controlled-failures",
    action="store_true",
    help="Measure controlled races and persistent failures; exit2 when adoption gates fail",
)
parser.add_argument("--attempt-calibration", action="store_true",
                    help="Trace pinned JDBC/server attempts; exit2 for unmet observer gates")
parser.add_argument("--disposable-local-only", action="store_true", required=True)
parser.add_argument("--distribution-zip", type=Path, required=True)
parser.add_argument("--provider-jar", type=Path, required=True)
parser.add_argument("--java-home", type=Path, required=True)
parser.add_argument(
    "--report-dir",
    type=Path,
    required=True,
    help="New private directory outside the checkout",
)
args = parser.parse_args()
if args.attempt_calibration and args.controlled_failures:
    parser.error("Use one separately bounded qualification mode at a time")
S = Path(__file__).resolve().parent.parent
O = args.report_dir.expanduser().resolve()
if O.is_relative_to(S.parents[2]):
    parser.error("Report directory must be outside the checkout")
O.mkdir(mode=0o700, parents=False, exist_ok=False)
os.umask(0o077)
build = json.loads((S / "build-review.json").read_text())
review = json.loads((S / "runtime-review.json").read_text())
J = args.java_home.expanduser().resolve()
INPUT = dict(
    sha256=review["distribution_sha256"],
    h2_sha256=review["h2_sha256"],
    provider_jar=str(args.provider_jar.expanduser().resolve()),
    provider_sha256=build["jar_sha256"],
)
for name, value in build["source_inputs_sha256"].items():
    if hashlib.sha256((S / name).read_bytes()).hexdigest() != value:
        raise RuntimeError("Build source inputs differ: " + name)
version = subprocess.run(
    [str(J / "bin/java"), "-version"], capture_output=True, text=True, check=True
)
if 'version "21.' not in version.stderr:
    raise RuntimeError("This historical compatibility lab requires Java21")
LAB = Path(tempfile.mkdtemp(prefix="sg-keycloak-qualification-")).resolve()
LAB.chmod(0o700)
# Covers failures before process startup as well as the main finally block.
atexit.register(lambda: shutil.rmtree(LAB) if LAB.exists() else None)
(O / "lab-location.private.json").write_text(
    json.dumps(dict(root=str(LAB), new_disposable_only=True)) + "\n"
)
QUALIFICATION_EXIT = 0
sys.dont_write_bytecode = True
PROCS = []
RESULTS = []
env = {k: v for k, v in os.environ.items() if k in {"HOME", "TMPDIR", "LANG", "LC_ALL"}}
env.update(
    PATH=str(J / "bin") + ":/usr/bin:/bin",
    JAVA_HOME=str(J),
    JAVA_OPTS_APPEND="-Xms128m -Xmx768m -Djava.net.preferIPv4Stack=true -Duser.timezone=UTC",
    SG_LAB_ROOT=str(LAB),
    SG_LAB_AUDIT_LOG=str(LAB / "writes.tsv"),
)
TENANT = "11111111-1111-4111-8111-111111111111"
SUBJECT = "22222222-2222-4222-8222-222222222222"
CLIENT = "33333333-3333-4333-8333-333333333333"
MGMT = "44444444-4444-4444-8444-444444444444"
MC = "55555555-5555-4555-8555-555555555555"
FOREIGN = "66666666-6666-4666-8666-666666666666"
AUD = "urn:sentinelgrid:issuer-association"
CONTRACT = "keycloak-registration-association-v1"
realm = "sg-lab-" + secrets.token_hex(4)
realmId = "realm-" + secrets.token_hex(8)


def freeport():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


port = freeport()
dbport = freeport()
origin = f"https://localhost:{port}"
issuer = origin + "/realms/" + realm
# Pinned vendor H2 dev-file mapper forces sa/password; new loopback-only lab, never deployment credentials.
DBPWD = "password"
ADMINPWD = secrets.token_urlsafe(32)
MGMTSECRET = secrets.token_urlsafe(32)
env.update(
    SG_LAB_JDBC=f"jdbc:h2:tcp://127.0.0.1:{dbport}/./sglab;NON_KEYWORDS=VALUE;DB_CLOSE_DELAY=-1",
    SG_LAB_DB_PASSWORD=DBPWD,
)
if args.controlled_failures or args.attempt_calibration:
    (LAB / "statement-observer-owned").write_text("fresh disposable lab")
    env["SG_LAB_FIXTURE_NONCE"] = secrets.token_hex(24)
    env["SG_LAB_JDBC"] += (
        ";DATABASE_EVENT_LISTENER='ai.sentinelgrid.keycloak.lab.LabStatementListener'"
    )
DBPROC = None
KC = None
attempt = 0
# An explicit small bookkeeping exclusion; all other vendor base tables are protected by default.
BOOKKEEP = {
    "EVENT_ENTITY",
    "ADMIN_EVENT_ENTITY",
    "OFFLINE_USER_SESSION",
    "OFFLINE_CLIENT_SESSION",
    "OFFLINE_USER_SESSION_NOTE",
    "OFFLINE_CLIENT_SESSION_NOTE",
}


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(cmd, **kwargs):
    return subprocess.run(
        [str(x) for x in cmd],
        env=env,
        capture_output=True,
        text=True,
        check=True,
        **kwargs,
    )


def launch(cmd, name):
    f = (LAB / (name + ".log")).open("a")
    p = subprocess.Popen(
        [str(x) for x in cmd],
        env=env,
        stdout=f,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    f.close()
    PROCS.append(p)
    return p


def stop(p):
    if p and p.poll() is None:
        os.killpg(p.pid, signal.SIGTERM)
        try:
            p.wait(timeout=25)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait(timeout=10)


def wait_port(p, prt):
    for _ in range(100):
        if p.poll() is not None:
            raise RuntimeError("Lab process exited before readiness")
        try:
            with socket.create_connection(("127.0.0.1", prt), timeout=0.2):
                return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError("Lab listener unavailable")


def db(action, *args):
    return run(
        [
            J / "bin/java",
            "-cp",
            classpath,
            "ai.sentinelgrid.keycloak.lab.LabDatabase",
            action,
            *args,
        ],
        timeout=30,
    ).stdout


def snapshot():
    data = {}
    for l in db("snapshot").splitlines():
        t, n, h = l.split("\t")
        data[t] = dict(rows=int(n), sha256=h)
    return data


def audit():
    p = LAB / "writes.tsv"
    return p.read_text().splitlines() if p.exists() else []


def start_kc(enabled=True, grants=True):
    global attempt, KC
    attempt += 1
    grant = dict(
        issuer=issuer,
        realm_id=realmId,
        iam_audience="review-client",
        management_client_id="association-reader",
        management_subject_id=MGMT,
        client_uuid=CLIENT,
        client_id="ticket-reader",
        subject_id=SUBJECT,
        tenant_id=TENANT,
    )
    conf = home / "conf/keycloak.conf"
    conf.write_text(
        "\n".join(
            [
                "db=dev-file",
                "db-url=" + env["SG_LAB_JDBC"],
                "db-username=sa",
                "hostname=" + origin,
                "http-host=127.0.0.1",
                "http-enabled=false",
                "https-port=" + str(port),
                "https-certificate-file=" + str(LAB / "cert.pem"),
                "https-certificate-key-file=" + str(LAB / "key.pem"),
                "cache=local",
                "spi-realm-restapi-extension-sentinelgrid-registration-enabled="
                + str(enabled).lower(),
                "spi-realm-restapi-extension-sentinelgrid-registration-grants-json="
                + json.dumps(
                    dict(version=1, grants=[grant] if grants else []),
                    separators=(",", ":"),
                ),
            ]
        )
        + "\n"
    )
    conf.chmod(0o600)
    env.update(
        KC_DB_PASSWORD=DBPWD,
        KC_BOOTSTRAP_ADMIN_USERNAME="lab-admin",
        KC_BOOTSTRAP_ADMIN_PASSWORD=ADMINPWD,
    )
    KC = launch(
        [home / "bin/kc.sh", "start", "--import-realm", "--verbose"],
        f"keycloak-{attempt}",
    )
    for _ in range(200):
        if KC.poll() is not None:
            raise RuntimeError(
                "Keycloak lab exited; inspect retained private startup log"
            )
        try:
            r = http.get(issuer + "/.well-known/openid-configuration")
            if r.status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.3)
    raise RuntimeError("Keycloak lab readiness timed out")


def hardcoded(name, value, jsonType="String"):
    return dict(
        name="sg-" + name,
        protocol="openid-connect",
        protocolMapper="oidc-hardcoded-claim-mapper",
        config={
            "claim.name": name,
            "claim.value": json.dumps(value, separators=(",", ":"))
            if jsonType == "JSON"
            else value,
            "jsonType.label": jsonType,
            "access.token.claim": "true",
            "id.token.claim": "false",
            "userinfo.token.claim": "false",
        },
    )


def token():
    r = http.post(
        issuer + "/protocol/openid-connect/token",
        data={"grant_type": "client_credentials"},
        auth=httpx.BasicAuth("association-reader", MGMTSECRET),
    )
    assert r.status_code == 200, "Lab token acquisition failed"
    return r.json()["access_token"]


def admin_token():
    r = http.post(
        origin + "/realms/master/protocol/openid-connect/token",
        data={
            "grant_type": "password",
            "client_id": "admin-cli",
            "username": "lab-admin",
            "password": ADMINPWD,
        },
    )
    assert r.status_code == 200, "Lab setup authentication failed"
    return r.json()["access_token"]


def admin(method, path, **kwargs):
    r = http.request(
        method,
        origin + "/admin/realms/" + realm + path,
        headers={"Authorization": "Bearer " + admin_token()},
        **kwargs,
    )
    assert r.status_code in {200, 201, 204}, "Lab fixture administration failed"
    return r


def probe(
    name,
    tok=None,
    expected=503,
    method="GET",
    suffix="",
    body=None,
    extra=None,
    headers=None,
    target=None,
):
    # Token acquisition and deliberate fixture mutations are always outside observation measurement.
    if tok is None:
        tok = token()
    before = snapshot()
    marks = len(audit())
    confhash = digest(home / "conf/keycloak.conf")
    hs = [("Authorization", "Bearer " + tok)] if headers is None else headers
    hs += extra or []
    r = http.request(
        method,
        issuer
        + "/sentinelgrid-registration/v1/clients/"
        + (target or CLIENT)
        + "/association"
        + suffix,
        headers=hs,
        content=body,
    )
    after = snapshot()
    writes = audit()[marks:]
    protected = [l for l in writes if l.split("\t")[0] not in BOOKKEEP]
    changed = [
        t
        for t in set(before) | set(after)
        if t not in BOOKKEEP and before.get(t) != after.get(t)
    ]
    result = dict(
        case=name,
        status=r.status_code,
        expected=expected,
        passed=r.status_code == expected
        and not protected
        and not changed
        and digest(home / "conf/keycloak.conf") == confhash,
        protected_write_attempts=len(protected),
        protected_snapshot_changes=changed,
        bookkeeping_write_attempts=len(writes) - len(protected),
        configuration_unchanged=digest(home / "conf/keycloak.conf") == confhash,
    )
    if r.status_code == 200:
        value = r.json()
        result["minimal_response"] = set(value) == {
            "contract",
            "issuer",
            "realm_id",
            "client_uuid",
            "client_id",
            "subject_id",
            "tenant_id",
            "client_enabled",
            "subject_enabled",
            "observed_at",
        }
        result["exact_attribution"] = (
            all(
                value.get(k) == v
                for k, v in dict(
                    contract=CONTRACT,
                    issuer=issuer,
                    realm_id=realmId,
                    client_uuid=CLIENT,
                    client_id="ticket-reader",
                    subject_id=SUBJECT,
                    tenant_id=TENANT,
                ).items()
            )
            and type(value.get("observed_at")) is int
            and abs(time.time() - value["observed_at"]) < 10
            and type(value.get("client_enabled")) is bool
            and type(value.get("subject_enabled")) is bool
        )
        result["passed"] &= result["exact_attribution"]
        result["no_store"] = r.headers.get("cache-control") == "no-store"
        result["passed"] &= result["minimal_response"] and result["no_store"]
    if r.status_code == 503:
        result["generic_no_store_denial"] = (
            r.json() == {"detail": "Association observation unavailable"}
            and r.headers.get("cache-control") == "no-store"
        )
        result["passed"] &= result["generic_no_store_denial"]
    RESULTS.append(result)
    (O / "runtime-cases.private.json").write_text(json.dumps(RESULTS, indent=2) + "\n")
    if not result["passed"]:
        (O / "last-response.private.txt").write_text(r.text[:2000])
        raise AssertionError(
            "Lab case failed: "
            + name
            + " status="
            + str(r.status_code)
            + " changes="
            + ",".join(changed)
        )
    return r


try:
    # Copy only the verified distribution into a newly created private lab.
    archive = args.distribution_zip.expanduser().resolve()
    assert digest(archive) == INPUT["sha256"]
    with zipfile.ZipFile(archive) as z:
        z.extractall(LAB)
    home = LAB / "keycloak-26.0.6"
    for p in (home / "bin").glob("*.sh"):
        p.chmod(0o700)
    h2 = next((home / "lib").rglob("com.h2database.h2-*.jar"))
    assert digest(h2) == INPUT["h2_sha256"]
    provider = Path(INPUT["provider_jar"])
    assert digest(provider) == INPUT["provider_sha256"]
    shutil.copyfile(provider, home / "providers/sg-association.jar")
    classes = LAB / "observer-classes"
    classes.mkdir()
    run(
        [
            J / "bin/javac",
            "-proc:none",
            "-cp",
            h2,
            "-d",
            classes,
            *sorted((S / "qualification/java").glob("*.java")),
        ],
        timeout=30,
    )
    observer = LAB / "lab-observer.jar"
    run([J / "bin/jar", "--create", "--file", observer, "-C", classes, "."], timeout=30)
    shutil.copyfile(observer, home / "providers/lab-observer.jar")
    classpath = str(h2) + os.pathsep + str(observer)
    if args.attempt_calibration:
        from attempts.observer import build as build_attempt_observer

        build_attempt_observer(globals())
    (LAB / "db").mkdir()
    DBPROC = launch(
        [
            J / "bin/java",
            "-Dh2.bindAddress=127.0.0.1",
            "-cp",
            classpath,
            "org.h2.tools.Server",
            "-tcp",
            "-tcpPort",
            str(dbport),
            "-ifNotExists",
            "-baseDir",
            LAB / "db",
        ],
        "h2",
    )
    wait_port(DBPROC, dbport)
    db("snapshot")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]))
        .issuer_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")]))
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    (LAB / "cert.pem").write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (LAB / "key.pem").write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    (LAB / "key.pem").chmod(0o600)
    http = httpx.Client(
        verify=ssl.create_default_context(cafile=str(LAB / "cert.pem")),
        trust_env=False,
        follow_redirects=False,
        timeout=10,
    )
    target = dict(
        issuer=issuer,
        client_uuid=CLIENT,
        client_id="ticket-reader",
        subject_id=SUBJECT,
        tenant_id=TENANT,
    )
    mappers = [
        hardcoded("tenant_id", TENANT),
        hardcoded("sg_principal_type", "workload"),
        hardcoded("sg_identity_contract", CONTRACT),
        hardcoded("sg_permissions", ["iam.read_workload_association"], "JSON"),
        hardcoded("sg_registration_target", target, "JSON"),
    ]
    mappers += [
        dict(
            name="aud-" + str(i),
            protocol="openid-connect",
            protocolMapper="oidc-audience-mapper",
            config={
                "included.custom.audience": aud,
                "access.token.claim": "true",
                "id.token.claim": "false",
            },
        )
        for i, aud in enumerate(["review-client", AUD])
    ]

    def client(id, name, secret):
        return dict(
            id=id,
            clientId=name,
            enabled=True,
            protocol="openid-connect",
            publicClient=False,
            clientAuthenticatorType="client-secret",
            secret=secret,
            serviceAccountsEnabled=False,
            standardFlowEnabled=False,
            directAccessGrantsEnabled=False,
            implicitFlowEnabled=False,
            fullScopeAllowed=False,
            defaultClientScopes=[],
            optionalClientScopes=[],
            attributes={
                "access.token.lifespan": "30",
                "use.refresh.tokens": "false",
                "client_credentials.use_refresh_token": "false",
            },
        )

    c = client(CLIENT, "ticket-reader", secrets.token_urlsafe(32))
    m = client(MC, "association-reader", MGMTSECRET)
    m["protocolMappers"] = mappers
    seed = dict(
        id=realmId,
        realm=realm,
        enabled=True,
        accessTokenLifespan=30,
        sslRequired="all",
        clients=[c, m],
        users=[
            dict(
                id=SUBJECT,
                username="service-account-ticket-reader",
                enabled=True,
                serviceAccountClientId="ticket-reader",
            ),
            dict(
                id=MGMT,
                username="service-account-association-reader",
                enabled=True,
                serviceAccountClientId="association-reader",
            ),
        ],
    )
    imp = home / "data/import"
    imp.mkdir(parents=True)
    (imp / "sg-lab-realm.json").write_text(json.dumps(seed))
    (imp / "sg-lab-realm.json").chmod(0o600)
    start_kc()
    # Avoid the pinned vendor's startup-import service-account cache/organization bug.
    # Enable through realm-bound Admin REST after import, entirely outside observation measurement.
    for fixture in (c, m):
        fixture["serviceAccountsEnabled"] = True
        admin("PUT", "/clients/" + fixture["id"], json=fixture)
    tables = int(db("install").strip())
    baseline = snapshot()
    (O / "observer-inventory.private.json").write_text(
        json.dumps(
            dict(
                instrumented_tables=tables,
                tables=sorted(baseline),
                bookkeeping_exclusions=sorted(BOOKKEEP),
                before_row_fingerprints=baseline,
                observer_implementation_sha256={
                    p.name: digest(p) for p in (S / "qualification/java").glob("*.java")
                },
                attempts_recorded_outside_transaction=True,
                rolled_back_attempts_counted=True,
                no_row_values_logged=True,
            ),
            indent=2,
        )
        + "\n"
    )
    tok = token()
    payload = json.loads(base64.urlsafe_b64decode(tok.split(".")[1] + "=="))
    (O / "issued-token-shape.private.json").write_text(
        json.dumps(
            dict(
                keys=sorted(payload),
                typ=payload.get("typ"),
                aud=payload.get("aud"),
                jti_canonical=payload.get("jti") is not None,
                session_claims=[
                    n
                    for n in ["sid", "session_state", "preferred_username"]
                    if n in payload
                ],
                lifetime=payload["exp"] - payload["iat"],
            ),
            indent=2,
        )
        + "\n"
    )
    probe("valid_real_issuer_and_JPA", tok, 200)
    print(json.dumps(dict(positive_runtime_passed=True, tables=tables)), flush=True)
    if args.controlled_failures:
        from controlled_failures import run as controlled_run

        controlled = controlled_run(globals())
        QUALIFICATION_EXIT = 0 if controlled["adoption_gate_passed"] else 2

    if args.attempt_calibration:
        from attempts.observer import calibrate as calibrate_attempts

        calibrate_attempts(globals())

    # Runs only inside lab.py's newly created realm. All fixture changes precede measurement.
    import concurrent.futures
    import copy

    def patch_client(id, **changes):
        value = admin("GET", "/clients/" + id).json()
        value.update(changes)
        admin("PUT", "/clients/" + id, json=value)

    def patch_user(id, **changes):
        value = admin("GET", "/users/" + id).json()
        value.update(changes)
        admin("PUT", "/users/" + id, json=value)

    def fixture_sql(sql):
        f = LAB / "fixture.sql"
        f.write_text(sql)
        db("sql", str(f))
        f.unlink()

    def clear_caches():
        for scope in ["user", "realm"]:
            admin("POST", "/clear-" + scope + "-cache")

    probe("warm_local_association", expected=200)
    # TLS failures are measured separately: the resource is never reached.
    for name, context, hostname in [
        ("untrusted_certificate", ssl.create_default_context(), "localhost"),
        (
            "wrong_TLS_hostname",
            ssl.create_default_context(cafile=str(LAB / "cert.pem")),
            "wrong.synthetic.invalid",
        ),
    ]:
        before = snapshot()
        mark = len(audit())
        failed = False
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=5) as raw:
                with context.wrap_socket(raw, server_hostname=hostname):
                    pass
        except ssl.SSLCertVerificationError:
            failed = True
        after = snapshot()
        writes = audit()[mark:]
        assert failed and before == after and not writes
        RESULTS.append(
            dict(
                case=name,
                passed=True,
                TLS_verification_rejected=True,
                protected_write_attempts=0,
                protected_snapshot_changes=[],
                bookkeeping_write_attempts=0,
            )
        )
    probe("missing_bearer", headers=[])
    t = token()
    parts = t.split(".")
    sig = bytearray(base64.urlsafe_b64decode(parts[2] + "=="))
    sig[0] ^= 1
    probe(
        "forged_signature",
        tok=".".join(parts[:2] + [base64.urlsafe_b64encode(sig).rstrip(b"=").decode()]),
    )
    probe(
        "duplicate_bearer",
        headers=[("Authorization", "Bearer " + t), ("Authorization", "Bearer " + t)],
    )
    probe("cookie_hint", extra=[("Cookie", "KEYCLOAK_SESSION=synthetic")])
    probe("tenant_hint", extra=[("X-Tenant-ID", TENANT)])
    probe("query_hint", suffix="?tenant_id=" + TENANT)
    probe("body_forbidden", body=b"{}")
    probe("chunked_body_forbidden", body=b"", extra=[("Transfer-Encoding", "chunked")])
    probe("encoded_path_forbidden", target=CLIENT.replace("-", "%2D", 1))
    probe("POST_not_routed", method="POST", expected=405)
    probe("HEAD_forbidden", method="HEAD", expected=405)
    probe("wrong_uuid", target=FOREIGN)
    probe("wrong_origin", extra=[("Host", "127.0.0.1:" + str(port))])
    r = http.post(
        issuer + "/protocol/openid-connect/token",
        data={"grant_type": "client_credentials"},
        auth=httpx.BasicAuth("ticket-reader", c["secret"]),
    )
    assert r.status_code == 200
    probe("ungranted_real_workload", tok=r.json()["access_token"])
    # Real issuer-signed, separately incorrect claim profiles, not unsigned test claims.
    owned = admin("GET", "/clients/" + MC).json()
    for name, claim, value, kind in [
        ("wrong_tenant", "tenant_id", FOREIGN, "String"),
        ("wrong_contract", "sg_identity_contract", "workload-v1", "String"),
        ("missing_permission", "sg_permissions", [], "JSON"),
        (
            "wrong_target",
            "sg_registration_target",
            {**target, "subject_id": FOREIGN},
            "JSON",
        ),
        ("session_hint", "sid", FOREIGN, "String"),
        ("username_hint", "preferred_username", "synthetic-fallback", "String"),
    ]:
        changed = copy.deepcopy(owned)
        changed["protocolMappers"] = [
            m
            for m in changed["protocolMappers"]
            if m.get("config", {}).get("claim.name") != claim
        ] + [hardcoded(claim, value, kind)]
        admin("PUT", "/clients/" + MC, json=changed)
        probe("native_signed_" + name)
        admin("PUT", "/clients/" + MC, json=owned)
    # Native revocation and management enabled states: token minted before fixture change.
    t = token()
    patch_client(MC, notBefore=int(time.time()) + 2)
    probe("native_client_revoked", tok=t)
    patch_client(MC, notBefore=0)
    t = token()
    patch_client(MC, enabled=False)
    probe("native_management_client_disabled", tok=t)
    patch_client(MC, enabled=True)
    t = token()
    patch_user(MGMT, enabled=False)
    probe("native_management_subject_disabled", tok=t)
    patch_user(MGMT, enabled=True)
    # Server-issued expiry, with a short bounded wait and no local token signer.
    short = copy.deepcopy(owned)
    short["attributes"]["access.token.lifespan"] = "1"
    admin("PUT", "/clients/" + MC, json=short)
    t = token()
    time.sleep(2)
    probe("native_expired", tok=t)
    admin("PUT", "/clients/" + MC, json=owned)
    # Inspection must report disabled target state without enabling it.
    patch_client(CLIENT, enabled=False)
    assert (
        probe("disabled_target_client_inspection", expected=200).json()[
            "client_enabled"
        ]
        is False
    )
    patch_client(CLIENT, enabled=True)
    patch_user(SUBJECT, enabled=False)
    assert (
        probe("disabled_target_subject_inspection", expected=200).json()[
            "subject_enabled"
        ]
        is False
    )
    patch_user(SUBJECT, enabled=True)
    probe("restored_enabled_observation", expected=200)
    # Instrumentation calibration must observe a write attempt even when the DB rolls it back.
    before = snapshot()
    mark = len(audit())
    fixture_sql(
        "BEGIN; UPDATE USER_ENTITY SET ENABLED=FALSE WHERE ID='"
        + SUBJECT
        + "'; ROLLBACK;"
    )
    assert snapshot() == before and any(
        l.startswith("USER_ENTITY\t") for l in audit()[mark:]
    )
    (O / "observer-calibration.private.json").write_text(
        json.dumps(
            dict(
                rollback_attempt_detected=True,
                persistent_snapshot_unchanged=True,
                provider_not_invoked=True,
            )
        )
        + "\n"
    )
    # Deliberate JPA store corruption is lab-only; clear actual vendor caches before observing.
    fixture_sql(
        "UPDATE USER_ENTITY SET SERVICE_ACCOUNT_CLIENT_LINK='"
        + FOREIGN
        + "' WHERE ID='"
        + SUBJECT
        + "'"
    )
    clear_caches()
    probe("rebound_local_link")
    fixture_sql(
        "UPDATE USER_ENTITY SET SERVICE_ACCOUNT_CLIENT_LINK='"
        + CLIENT
        + "' WHERE ID='"
        + SUBJECT
        + "'"
    )
    clear_caches()
    probe("repaired_fixture_only", expected=200)
    fixture_sql(
        "UPDATE USER_ENTITY SET FEDERATION_LINK='synthetic-unsupported' WHERE ID='"
        + SUBJECT
        + "'"
    )
    clear_caches()
    probe("unsupported_federation_link")
    fixture_sql(
        "UPDATE USER_ENTITY SET FEDERATION_LINK=NULL WHERE ID='" + SUBJECT + "'"
    )
    clear_caches()
    probe("local_fixture_restored", expected=200)
    # Concurrent read-only retries share one measured window; no concurrent fixture mutations.
    t = token()
    before = snapshot()
    mark = len(audit())

    def concurrent_read(i):
        r = http.get(
            issuer + "/sentinelgrid-registration/v1/clients/" + CLIENT + "/association",
            headers={"Authorization": "Bearer " + t},
        )
        return r.status_code

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        statuses = list(pool.map(concurrent_read, range(12)))
    after = snapshot()
    writes = audit()[mark:]
    changed = [n for n in before if n not in BOOKKEEP and before[n] != after[n]]
    protected = [l for l in writes if l.split("\t")[0] not in BOOKKEEP]
    assert statuses == [200] * 12 and not changed and not protected
    RESULTS.append(
        dict(
            case="concurrent_read_retries_12",
            passed=True,
            statuses=statuses,
            protected_write_attempts=0,
            protected_snapshot_changes=[],
            bookkeeping_write_attempts=len(writes),
        )
    )
    # Restart with the same newly created local DB, both closed configurations, then re-enable only the lab.
    for name, enabled, grants, expected in [
        ("empty_owned_grants", True, False, 503),
        ("default_disabled", False, True, 404),
        ("restart_valid_local", True, True, 200),
    ]:
        stop(KC)
        start_kc(enabled, grants)
        probe(name, expected=expected)
    # A server outage is transport unavailability, never an observation or successful retry.
    stop(KC)
    before = snapshot()
    mark = len(audit())
    unavailable = False
    try:
        http.get(
            issuer + "/sentinelgrid-registration/v1/clients/" + CLIENT + "/association"
        )
    except httpx.ConnectError:
        unavailable = True
    assert unavailable and snapshot() == before and len(audit()) == mark
    RESULTS.append(
        dict(
            case="server_outage",
            passed=True,
            transport_unavailable=True,
            protected_write_attempts=0,
            protected_snapshot_changes=[],
            bookkeeping_write_attempts=0,
        )
    )
    start_kc()
    probe("outage_recovery", expected=200)
    # Delete the actual target service account; observation must not recreate it.
    admin("DELETE", "/users/" + SUBJECT)
    clear_caches()
    probe("deleted_target_subject")
    probe("deleted_target_retry")
    stop(KC)
    start_kc()
    probe("deleted_target_after_restart")
    # Same client/name can create a new account during explicit fixture provisioning, never as observation.
    patch_client(CLIENT, serviceAccountsEnabled=False)
    patch_client(CLIENT, serviceAccountsEnabled=True)
    clear_caches()
    created = admin("GET", "/clients/" + CLIENT + "/service-account-user").json()
    assert created["id"] != SUBJECT
    probe("recreated_same_name_different_id")
    admin("DELETE", "/clients/" + CLIENT)
    clear_caches()
    probe("deleted_target_client")
    (O / "runtime-cases.private.json").write_text(json.dumps(RESULTS, indent=2) + "\n")
    print(
        json.dumps(
            dict(
                runtime_cases=len(RESULTS), all_passed=all(r["passed"] for r in RESULTS)
            )
        ),
        flush=True,
    )

except BaseException as e:
    if isinstance(e, subprocess.CalledProcessError):
        (O / "lab-tool-failure.private.log").write_text(e.stderr or "")
    (O / "runtime-failure.private.json").write_text(
        json.dumps(
            dict(error=type(e).__name__, message=str(e), lab_only=True), indent=2
        )
        + "\n"
    )
    raise
finally:
    for p in reversed(PROCS):
        stop(p)
    if args.controlled_failures or args.attempt_calibration:
        for name in ["statements.tsv", "writes.tsv"]:
            if (LAB / name).exists():
                shutil.copyfile(LAB / name, O / ("lab-" + name))
    for log in LAB.glob("*.log"):
        shutil.copyfile(log, O / ("lab-" + log.name.replace(".log", ".private.log")))
    cleanup = dict(
        all_processes_exited=all(p.poll() is not None for p in PROCS),
        processes=len(PROCS),
        private_lab_removed=False,
        no_existing_services_or_data_accessed=True,
    )
    if "http" in globals():
        http.close()
    shutil.rmtree(LAB)
    cleanup["private_lab_removed"] = not LAB.exists()
    (O / "cleanup.private.json").write_text(json.dumps(cleanup, indent=2) + "\n")
    print(json.dumps(cleanup), flush=True)

if args.attempt_calibration:
    from attempts.observer import analyze as analyze_attempts

    evidence = analyze_attempts(O, protected_values=(env["SG_LAB_ATTEMPT_CANARY"],
                                                      env["SG_LAB_FIXTURE_NONCE"],
                                                      ADMINPWD, MGMTSECRET, c["secret"]))
    QUALIFICATION_EXIT = 0 if evidence["all_attribution_and_observer_health_gates_passed"] else 2
    print(json.dumps(dict(attempt_events=evidence["events"],
                          observer_gate_passed=evidence["all_attribution_and_observer_health_gates_passed"])), flush=True)

if QUALIFICATION_EXIT:
    raise SystemExit(QUALIFICATION_EXIT)
