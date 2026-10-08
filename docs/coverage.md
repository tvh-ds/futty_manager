# Coverage and publication gate

## Current candidates

Status: **held — no provider account or display approval configured**. `config/publication.json` remains false. Current API data is fictional. A real candidate release requires a common completed season from 2024/25, England/Spain/Germany/Italy/France, all eight roles in each league with exposure, canonical identities, sourced measurements and documented public display permission. Release validation refuses synthetic evidence even when the approval flag is set.

The provisional API-Football probe checks season/sample access and reports pagination/declared fields. It cannot establish complete goalkeeper/tactical/footedness coverage or licensing from a sample. Reviewed outfield role overrides are required; an empty override file quarantines unresolved broad positions. Ingestion/quarantine reports must be inspected before publication. Freshness, completed fixture counts, identity/stint mapping, metric semantics and all provider entitlements require real verification.

Run `scout probe --season 2024`, then quota-limited `scout ingest --season 2024` only after configuring the free account. Never mark approval true merely to make a test pass. No paid or older-season fallback is authorized.

## Historical research

Separate source: [StatsBomb Open Data](https://github.com/hudl/open-data). Locally archived revision `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb` yielded 34 male senior Bundesliga 2023/24 matches, 916 valid in-match shots and zero quarantined shots. Shootouts are excluded. Distance uses normalized provider pitch coordinates, not metres. Match dates define chronological folds. Source files/license/checksums live under the ignored historical directory.

This biased subset supports model implementation/research only. It does not satisfy the current candidate release, five-league completeness, transfer modelling or publication gate. Review the archived license and required [source/logo attribution](https://github.com/hudl/open-data#terms--conditions) before public analysis publication.
