# Consolidated Flyway source

Current schema-change guidance is [database changes](../../docs/development/database-changes.md)
and [AGENTS.md](../../docs/AGENTS.md). Pair ORM and Flyway changes, keep globally unique
versions, and explicitly target the schema. Do not refresh or overwrite V001 to
apply a new schema change. Existing numbered history is retained for review.

The supported preview uses offline V013/model contract tests and requires no database.
A fresh install, migration upgrade, or restore has not been qualified here.
