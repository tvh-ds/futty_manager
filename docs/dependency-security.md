# Dependency verification

The frontend audit initially identified GHSA-82fw-gwwq-j7x9 in Vitest's development mock server. Vitest was upgraded to 4.1.11; subsequent install/audit reported zero advisories. Tests run in batch mode with loopback development servers.

Python's installed optional ML profile reported CVE-2026-41066 in socceraction's pinned lxml 4.9.4. Scout has no XML ingestion and uses the JSON StatsBomb adapter, but retains a patched lxml through an explicit uv dependency override `>=6.1,<7`. The legacy upstream `<5` constraint is incompatible with the security fix. Validate StatsBomb/SPADL/xT imports and execution after changes; no compatibility guarantee is claimed for socceraction's unused XML adapters. Do not ignore this advisory or publish an environment with the original pinned parser.

Native audit commands are `npm audit` and `pip-audit --local`. Audit installed optional profiles separately from the lean serving environment. Advisory service results reflect the time of the check and are not a full code security assessment. Raw advisory reports are generated under ignored `artifacts/`.
