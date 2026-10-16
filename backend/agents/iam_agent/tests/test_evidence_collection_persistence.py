from app.services.evidence_collection import EvidenceCollectionService, EvidenceType


class FakeKeycloakClient:
    def list_users(self):
        return [
            {"id": "user-1", "enabled": True},
            {"id": "user-2", "enabled": False},
        ]

    def get_authorization_policies(self):
        return [{"id": "policy-1", "name": "Admin policy", "type": "role", "logic": "POSITIVE"}]

    def get_user_roles(self, user_id):
        return [{"name": "user"}, {"name": "admin"}] if user_id == "user-1" else []


class FakeRepositoryClient:
    def __init__(self):
        self.evidence_items = []
        self.collection_tasks = []

    def create_evidence_item(self, payload):
        self.evidence_items.append(payload)
        return {
            "id": f"ev-{len(self.evidence_items)}",
            "idempotency_key": payload["idempotency_key"],
            "control_links": payload["control_links"],
        }

    def create_collection_task(self, payload):
        self.collection_tasks.append(payload)
        return {
            "id": f"task-{len(self.collection_tasks)}",
            "status": payload["status"],
            "idempotency_key": payload["idempotency_key"],
        }


def test_iam_evidence_collection_persists_real_outputs_and_tasks_for_placeholders():
    repository = FakeRepositoryClient()
    service = EvidenceCollectionService(FakeKeycloakClient())

    result = service.collect_control_evidence(
        "AC-2",
        [EvidenceType.CONFIGURATION, EvidenceType.AUDIT_LOG],
        tenant_id="11111111-1111-1111-1111-111111111111",
        repository_client=repository,
        actor_id="user-123",
    )

    assert result["repository"]["status"] == "completed"
    assert len(repository.evidence_items) == 1
    assert repository.evidence_items[0]["source_system"] == "iam_agent"
    assert repository.evidence_items[0]["metadata"]["raw_evidence"]["total_users"] == 2
    assert repository.evidence_items[0]["control_links"][0]["framework_id"] == "soc2"
    assert repository.evidence_items[0]["control_links"][0]["control_id"] == "CC6.2"
    assert repository.evidence_items[0]["idempotency_key"].startswith("iam:11111111-1111-1111-1111-111111111111:ac-2")

    task_statuses = {task["status"] for task in repository.collection_tasks}
    assert task_statuses == {"manual_evidence_required", "needs_connector"}
    assert any(task["metadata"]["evidence_key"] == "account_reviews" for task in repository.collection_tasks)
    assert any(task["metadata"]["evidence_type"] == "audit_log" for task in repository.collection_tasks)

    account_reviews = result["evidence"]["configuration"]["account_reviews"]
    assert account_reviews["status"] == "manual_evidence_required"
    assert account_reviews["audit_ready"] is False
    assert "review_frequency" not in account_reviews


def test_iam_authentication_evidence_does_not_persist_placeholder_success():
    repository = FakeRepositoryClient()
    service = EvidenceCollectionService(FakeKeycloakClient())

    result = service.collect_control_evidence(
        "IA-2",
        [EvidenceType.CONFIGURATION, EvidenceType.API_RESPONSE],
        tenant_id="22222222-2222-2222-2222-222222222222",
        repository_client=repository,
        actor_id="user-123",
    )

    assert repository.evidence_items == []
    assert len(repository.collection_tasks) == 3
    assert {task["status"] for task in repository.collection_tasks} == {
        "needs_connector",
        "manual_evidence_required",
    }
    assert result["evidence"]["configuration"]["multi_factor_authentication"]["audit_ready"] is False
    assert "mfa_enabled" not in result["evidence"]["configuration"]["multi_factor_authentication"]


def test_collection_without_repository_keeps_legacy_shape_but_marks_repository_not_configured():
    service = EvidenceCollectionService(FakeKeycloakClient())

    result = service.collect_control_evidence(
        "AC-3",
        [EvidenceType.POLICY_DOCUMENT],
        tenant_id="33333333-3333-3333-3333-333333333333",
    )

    assert result["control_id"] == "AC-3"
    assert "policy_document" in result["evidence"]
    assert result["repository"]["status"] == "not_configured"
