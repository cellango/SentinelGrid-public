# Archived workflows

The `*.yml.disabled` files in `../workflows/` are historical workflow definitions.
GitHub Actions does not load that extension. The active public check is
`source-preview.yml`; it requires no repository secrets or cloud access.

Deployment, Terraform apply, image builds, installer repackaging, and historical
integration/release suites are disabled for the source preview. Keep them disabled
until each supported runtime has its own validated release gate. Renaming an old
workflow back to `.yml` requires a separate security and correctness review,
including least-privilege permissions, immutable action pins, protected deployment
environments, artifact provenance, and fresh-install tests. Historical workflow
results do not establish that this snapshot is ready to deploy.
