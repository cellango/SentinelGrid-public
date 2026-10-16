# Product catalog compatibility fields

This is a source/schema compatibility reference, not a pricing sheet or hosted
service offer. Inspect [backend product_catalog.py](../../backend/libs/sg_core/product_catalog.py)
and [frontend catalog.ts](../../frontend/src/lib/product/catalog.ts) together when
changing serialized plan values or feature selection.

The code recognizes `protect`, `protect_defend`, and `protect_defend_comply`.
The legacy `protect_comply` alias normalizes to `protect_defend_comply`.
`plan_tier` is the canonical identity in these helpers; `package_name` remains a
compatibility field. `services_selected` expresses explicit options rather than
an independent plan identifier. The helpers normalize option shapes and apply
plan defaults; inspect callers before assuming every write path uses them.

These enums and UI labels do not define purchasable packages or prove feature
availability. Billing, signup provisioning, hosted support, and production
entitlements are outside the supported source preview. Internal pricing and
business strategy documents remain private.
