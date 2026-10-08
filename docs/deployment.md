# Deployment placeholders and prerequisites

Nothing in this repository has been deployed to Azure or Databricks. User instruction: keep account settings as placeholders. Workflows are implemented templates, not execution evidence.

## Azure

`infra/azure` passes Terraform validation using Terraform 1.13.5/AzureRM 4.81.0. Provider versions are locked. The configuration supplies ADLS Gen2 private containers, Key Vault, identities, OIDC, bounded telemetry, Static Web Apps Free, a scale-to-zero one-replica API and budget notifications. `deploy_api=false` prevents accidental application startup; Terraform initialization/validation does not provision anything.

Before any apply:

- Verify subscription credit eligibility, spending protection and resource availability in the portal.
- Bootstrap a dedicated, private, encrypted remote state account/container with locking and appropriate Blob Data Contributor access. Use `backend.hcl.example` with `terraform init -backend-config=...`. The state backend must exist before the main stack; no automatic bootstrap is claimed.
- Configure actual resource names/subscription/GitHub repository in ignored tfvars; review a saved plan.
- Put the Neon database URL, with TLS enabled, into the Key Vault secret `scout-database-url`. Do not put it into Terraform variables/state or an image.
- Grant the bootstrap operator the narrowly scoped role-assignment rights needed to provision managed-identity permissions. The routine deployment identity's Contributor role cannot administer RBAC; routine code releases use the application workflow.
- Publish the first validated serving release independently; readiness intentionally fails until it exists.

The runtime uses Key Vault references via managed identity; `AZURE_CLIENT_ID` selects the user-assigned identity for SDK calls. The frontend calls `VITE_API_URL` directly; generated Static Web Apps CSP permits only that HTTPS origin. Container-local frontend defaults to the nginx `/api` proxy.

Repository production variables: `CLOUD_ENABLED`, `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`, `AZURE_CONTAINER_APP`, `API_URL`, `CREDIT_RECORD`. Secret: `AZURE_STATIC_WEB_APPS_API_TOKEN`. Configure protected environments, CI acceptance and immutable image visibility before enabling. No GitHub remote/actions run exists yet. Workflow action references currently use version tags; review and pin commit SHAs before a public release.

## Databricks Free Edition

Use an existing managed catalog/schema/volume. The bundle targets `dev`/`production`, with finite serverless Python tasks using environment version 4. [Official serverless bundle configuration](https://docs.databricks.com/aws/en/dev-tools/bundles/examples#job-that-uses-serverless-compute) informs the template. The account/workspace is not configured and bundle validation/execution has not occurred.

Upload `bundle.json` **and** `sha256.txt` into `/Volumes/CATALOG/SCHEMA/VOLUME/input/RELEASE_ID/` using `scout cloud-transfer`. Configure bundle variables, authenticate using the workspace's supported method, then validate/deploy/run. Each task imports shared Python modules from the built wheel. The transform writes Delta tables and an immutable exported bundle; evaluation logs a 48-brief baseline report to managed MLflow. The CI runner downloads validated exports; no serving API workspace token is needed.

Set `DATABRICKS_ENABLED=true` only after the upload/download/job/MLflow integration probe succeeds. Configure the `batch` environment and narrowly scoped expiring workspace credential. Bump package versions when source changes to avoid serverless dependency caching. Do not assume Free Edition can fetch every dependency or directly mount ADLS.

Current limitations: Delta writes overwrite the dedicated analytical tables, whose history/versions must be recorded before a real production batch release; managed integration and Spark parity are still unverified. The Windows local attempt installed PySpark/Delta and Java, but failed at Spark startup because Hadoop native Windows support (`HADOOP_HOME`/winutils) was missing. No unofficial native binaries were installed. Use the supplied Linux CI job or a verified Linux/Docker environment for parity. Bundle export does not automatically activate PostgreSQL or upload ADLS yet; those guarded publication steps remain to implement.

## Monthly striker state

The separate monthly striker workflow requires an existing private Azure `backups` container and `AZURE_STORAGE_ACCOUNT` in the protected batch environment before live collection. It uses OIDC, the credit guard and checksummed, content-addressed archives with a conditional ETag pointer. It preserves raw snapshots, quota checkpoints and release history privately; GitHub receives only redacted status. Restore/save and corrupt-archive handling are tested locally, but no Azure roundtrip or remote monthly job has executed. First-run bootstrap is explicit. See `docs/striker-scoring.md` for commands, permissions, archive bounds and remaining acceptance gates.
