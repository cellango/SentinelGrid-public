# Flyway configuration and legacy migration references

Use [the current database source rules](../../docs/development/database-changes.md)
for new work. Configuration and older migration helpers here remain inspectable;
they are not a supported preview startup path. Do not use ad hoc/runtime schema
creation or rewrite a baseline in place. No migration is executed by preview checks.
