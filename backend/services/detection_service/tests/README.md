# Detection Service tests

This is experimental source for developer review. Read the
[root release scope](../../../../RELEASE_SCOPE.md) and the
[detection boundary](../../../../docs/architecture/gateway-identity.md#detection-scheduler-runtime-read-and-source-admission)
for current source and runtime limits.

From the repository root, run the required source target with the reviewed preview
dependencies:

```sh
make preview-detection-identity PYTHON=.venv/bin/python
```

The target mounts the actual HTTP app/gate/projector with the current IAM RSA
validator in a separate process, owned key/HTTP and runtime-state doubles. There
are no identity/admission overrides or fake APScheduler modules. It verifies exact
service-wide reader grants, unavailable state and operations, startup without DDL/
scheduling, direct lifecycle/session denials and no provider effects. It does not
start a real scheduler or qualify SDK, SQL/RLS, schema/data, rule evaluation or
alert/incident/ticket delivery.

The broader suite retains legacy rule/engine/integration tests with missing
fixtures such as `db_session`, `test_tenant_id` and sample rule/event data. It is
not a passing installation or runtime test. Earlier global scheduler/DDL substitutes
were removed; header/override-based mutation success tests now assert explicit
source unavailability. Rule and effect capabilities remain restoration requirements.
The selected `/api/v1/rules` routes differ from old tests' `/api/v1/detection/rules`
paths and from the SIEM Agent's separate versioned detection catalog. Full client/
proxy/status/schema compatibility still needs reconciliation; no alias is implied.
