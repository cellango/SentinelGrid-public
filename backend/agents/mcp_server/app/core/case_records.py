"""Opt-in case record tools. No provider dispatch or approval tool is exposed."""

from dataclasses import dataclass
import hmac, json, math, ssl, time
from urllib.parse import urlsplit
from types import MappingProxyType
import anyio, httpx
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, field_validator, ValidationError
from mcp.shared.exceptions import McpError
from mcp.types import (
    Tool,
    ToolAnnotations,
    CallToolResult,
    TextContent,
    ErrorData,
    INVALID_PARAMS,
)
from sg_core.action_contracts import (
    ProposalInput,
    ProposalRecord,
    canonical_uuid,
    canonical,
    digest,
    strict_json,
)
from sg_core.request_credentials import request_bearer_token
from sg_core.security import get_verified_request_identity
from sg_core.user_principals import require_user_binding

CASE_RECORD_MAPPING_VERSION = 1
WIRE_OPERATIONS = MappingProxyType(
    {
        "case_propose_action": "case.propose_action",
        "case_get_action_proposal": "case.get_action_proposal",
    }
)
MAX_REPLY = 65536


@dataclass(frozen=True)
class CaseRecordPolicy:
    origin: str
    operations: tuple[str, ...] = ("case.propose_action", "case.get_action_proposal")
    timeout_seconds: float = 5.0
    ca_bundle: str | None = None

    def __post_init__(self):
        if type(self.origin) is not str:
            raise ValueError("Owned origin must be a string")
        try:
            p = urlsplit(self.origin)
            port = p.port
        except (ValueError, TypeError):
            raise ValueError("Invalid owned case-record origin") from None
        if (
            p.scheme not in {"http", "https"}
            or not p.hostname
            or port == 0
            or p.username is not None
            or p.password is not None
            or p.path not in {"", "/"}
            or p.query
            or p.fragment
            or any(c in self.origin for c in "%\\?#")
            or any(ord(c) < 33 or ord(c) > 126 for c in self.origin)
        ):
            raise ValueError(
                "Expected an owned HTTP origin without credentials, path or overrides"
            )
        if (
            type(self.operations) is not tuple
            or not self.operations
            or any(type(v) is not str for v in self.operations)
            or len(set(self.operations)) != len(self.operations)
            or not set(self.operations) <= set(WIRE_OPERATIONS.values())
        ):
            raise ValueError("Unknown case-record operation")
        if (
            type(self.timeout_seconds) not in {int, float}
            or not math.isfinite(self.timeout_seconds)
            or not 0 < self.timeout_seconds <= 10
        ):
            raise ValueError("Expected bounded case-record deadline")
        if self.ca_bundle is not None and (
            type(self.ca_bundle) is not str or not self.ca_bundle
        ):
            raise ValueError("Owned CA bundle path required")


class RecordCreate(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    case_id: str
    request_key: str
    proposal: ProposalInput
    _ids = field_validator("case_id", "request_key")(canonical_uuid)


class RecordRead(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", frozen=True)
    case_id: str
    proposal_id: str
    _ids = field_validator("case_id", "proposal_id")(canonical_uuid)


class CaseRecordTools:
    def __init__(self, policy, get_caller):
        if not isinstance(policy, CaseRecordPolicy) or not callable(get_caller):
            raise TypeError("Owned record policy and transport context required")
        self.policy = policy
        self.get_caller = get_caller

    def tools(self):
        specs = [
            (
                "case_propose_action",
                RecordCreate,
                "Record an action proposal for review. This does not approve or execute it. Reuse the exact request_key and intent after an uncertain response.",
                False,
            ),
            (
                "case_get_action_proposal",
                RecordRead,
                "Read an action proposal accessible to the authenticated user. Status describes records; execution remains unavailable.",
                True,
            ),
        ]
        return [
            Tool(
                name=name,
                description=description,
                inputSchema=model.model_json_schema(),
                annotations=ToolAnnotations(
                    readOnlyHint=read_only,
                    destructiveHint=False,
                    idempotentHint=True,
                    openWorldHint=False,
                ),
            )
            for name, model, description, read_only in specs
            if WIRE_OPERATIONS[name] in self.policy.operations
        ]

    def unavailable(
        self, message="Case-record service unavailable; no execution was admitted"
    ):
        return CallToolResult(
            isError=True,
            content=[TextContent(type="text", text=message)],
            structuredContent={
                "execution_available": False,
                "record_status": "unavailable",
            },
        )

    async def call(self, request, name, arguments):
        operation = WIRE_OPERATIONS.get(name)
        if operation not in self.policy.operations:
            raise McpError(ErrorData(code=INVALID_PARAMS, message="Unknown MCP tool"))
        try:
            canonical(arguments)
            parsed = (
                RecordCreate if name == "case_propose_action" else RecordRead
            ).model_validate(arguments)
        except (ValueError, TypeError, RecursionError):
            raise McpError(
                ErrorData(code=INVALID_PARAMS, message="Invalid case-record arguments")
            ) from None
        try:
            caller = self.get_caller(request)
            identity = get_verified_request_identity(request)
            binding = require_user_binding(
                identity.payload(), request.app.state.user_principal_settings
            )
            if (
                str(caller.tenant_id) != identity.tenant_id
                or str(caller.actor_subject_id) != identity.user_id
                or caller.client_id != binding.client_id
                or operation not in caller.capabilities
                or caller.expires_at <= time.time()
            ):
                raise HTTPException(403, "Case-record capability denied")
            token = request_bearer_token(request)
            headers = {
                "Authorization": "Bearer " + token,
                "X-Tenant-ID": identity.tenant_id,
                "Accept": "application/json",
                "Accept-Encoding": "identity",
            }
            url = (
                self.policy.origin.rstrip("/")
                + "/api/v1/cases/"
                + parsed.case_id
                + "/action-proposals"
            )
            method = "POST" if name == "case_propose_action" else "GET"
            content = None
            if method == "POST":
                content = canonical(parsed.proposal.model_dump())
                headers["Idempotency-Key"] = parsed.request_key
                headers["Content-Type"] = "application/json"
            else:
                url += "/" + parsed.proposal_id
            verify = (
                ssl.create_default_context(cafile=self.policy.ca_bundle)
                if self.policy.ca_bundle
                else True
            )
            with anyio.fail_after(self.policy.timeout_seconds):
                async with httpx.AsyncClient(
                    timeout=httpx.Timeout(self.policy.timeout_seconds, pool=1.0),
                    verify=verify,
                    trust_env=False,
                    follow_redirects=False,
                    limits=httpx.Limits(max_connections=1, max_keepalive_connections=0),
                ) as client:
                    async with client.stream(
                        method, url, content=content, headers=headers
                    ) as response:
                        if response.status_code != (201 if method == "POST" else 200):
                            messages = {
                                401: "Case-record identity was rejected",
                                403: "Case-record permission denied",
                                404: "Case record not found",
                                409: "Case-record conflict or stale revision",
                                410: "Case-record proposal expired",
                                422: "Case-record proposal rejected",
                                429: "Case-record budget exceeded",
                            }
                            return self.unavailable(
                                messages.get(
                                    response.status_code,
                                    "Case-record service unavailable; retry the same request_key and intent after an uncertain submission",
                                )
                            )
                        types = response.headers.get_list("content-type")
                        encodings = response.headers.get_list("content-encoding")
                        if (
                            len(types) != 1
                            or types[0].split(";", 1)[0].strip().lower()
                            != "application/json"
                            or len(encodings) > 1
                            or encodings
                            and encodings[0].lower() != "identity"
                        ):
                            raise ValueError("Invalid case-record reply")
                        raw = bytearray()
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            raw.extend(chunk)
                            if len(raw) > MAX_REPLY:
                                raise ValueError("Case-record reply exceeds bounds")
            self.get_caller(request)  # Recheck expiry after a queued/remote operation.
            result = ProposalRecord.model_validate(
                strict_json(bytes(raw), limit=MAX_REPLY)
            )
            if (
                result.tenant_id != identity.tenant_id
                or result.case_id != parsed.case_id
            ):
                raise ValueError("Wrong case-record binding")
            if method == "GET":
                doc = result.proposal
                if doc is None or result.proposal_id != parsed.proposal_id:
                    raise ValueError("Missing exact proposal document")
                data = doc.model_dump(by_alias=True)
                if (
                    doc.tenant_id != identity.tenant_id
                    or doc.case_id != parsed.case_id
                    or doc.proposal_id != result.proposal_id
                    or doc.action_id != result.action_id
                    or doc.proposal_revision != result.proposal_revision
                    or not hmac.compare_digest(digest(data), result.proposal_hash)
                ):
                    raise ValueError("Proposal document integrity unavailable")
            elif result.proposal is not None:
                raise ValueError("Unexpected submission document")
            value = result.model_dump(by_alias=True, exclude_none=True)
            return CallToolResult(
                isError=False,
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps(
                            value, ensure_ascii=True, separators=(",", ":")
                        ),
                    )
                ],
                structuredContent=value,
            )
        except (
            HTTPException,
            httpx.HTTPError,
            TimeoutError,
            ValueError,
            TypeError,
            OSError,
            RecursionError,
            ValidationError,
        ):
            return self.unavailable()
