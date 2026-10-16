# Entity and evidence references

Status: code-linked source reference, October 15, 2026. The shared
[entity_model.py](../../backend/libs/sg_core/entity_model.py) builds story context
for alerts/incidents and related UI. It normalizes references; it is not a persisted
global relationship graph or proof of complete cross-module entity coverage.

Entity references use a type, ID, label, and domain, with optional role, provider,
href, and metadata. The represented entity types include identity, device,
resource, and AI application. Evidence references identify linked alerts, incidents,
tickets, detection rules, playbooks, attachments, CVEs, and findings. Read the
helper's normalization and deduplication behavior before extending it.

## Consumers to review

- [Gateway incident routes](../../backend/services/api_gateway/app/api/routes_incidents.py)
- [Gateway SIEM routes](../../backend/services/api_gateway/app/api/routes_siem.py)
- [Detection incident creation](../../backend/services/detection_service/app/services/incident_creator.py)
- [Frontend story types/helpers](../../frontend/src/lib/security/story.ts)
- [Story context panel](../../frontend/src/components/operator/StoryContextPanel.tsx)

An entity reference does not authorize access to the target record. Consumers
must preserve tenant scope and permission checks when resolving IDs or hrefs.
No unified finding API, complete entity persistence, live security graph, or
end-to-end story workflow is certified by the source preview.
