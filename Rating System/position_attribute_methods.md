# Shared rules for the eight proposed position registries

**Implemented provisional registries · 8 October 2026 · 2025/26 performance.** All nine position registries are active through [position_rating_weights_config.yaml](position_rating_weights_config.yaml). See [implementation and tuning](position_weights_implementation.md) for current coverage and collection limitations. These rules apply the current [rating system](rating_ranking_system.md), including uncapped scores, pooled peers and zero-filled-only redistribution; they do not revive older same-league or percentile-as-rating examples in `st_attributes.md`.

## Source and master contract

The inspected master is `data/master/2025-26-v2/master.sqlite`: 3,561 player/league rows, 227 wide columns, and retained provider observations. A player appearing in different leagues can have separate rows. These figures are not a verified unique-person count.

Use **Opta → PitchAPI → Understat → WhoScored** priority for an available, semantically compatible measurement. Merge features before choosing the source for a conflicting feature. An exact label match in the master is not sufficient to certify identical measurement definitions.

For derived ratios and rates, select a complete **provider-specific input bundle**, using preserved observations/provenance where necessary. Do not divide an Opta-selected numerator by PitchAPI attempts or minutes simply because both appear in the wide CSV. If the preferred provider lacks one required input, use the next complete compatible bundle. Keep the competing values and provenance. A recorded numeric zero is available and must not trigger source fallback.

Wide columns and raw appearance paths are distinguished in every position file. Raw appearance values are proposed inputs, not already-calculated season totals. WhoScored's master contribution is a captured sample rather than a complete five-league crawl. Understat remains private-use evidence. No source permission, database schema or release gate changes are made here.

## Exposure and aggregation

- `/90 = 90 × total / matched minutes`. Minutes must describe the same provider, season, team/league scope and observation window as the numerator. Zero minutes cannot produce a rate.
- Recompute percentages from numerator/denominator counts when available. Do not average match percentages. Match percentages without counts require a verified exposure-weighted approximation and an approximation label.
- Deduplicate raw appearances by provider player, fixture, team and period/appearance scope. Use a known fixture window and matching minutes; multiple retrievals are not multiple matches. Do not sum alternative season aggregates or duplicated transfer-stint samples.
- Captured partial-match totals must remain partial. Do not divide a partial numerator by a different provider's full-season minutes or extrapolate it silently.
- A season rating uses the existing 900-minute requirement. Raw inventory counts intentionally have no minimum-minute filter. A partial-window model must be separately versioned and not compared as a complete season rating.
- Preserve signed values, including goals above expectation and net progressive distance. Validate semantics before treating a negative distance as invalid; never turn it into an absolute value just to improve a score.

## Peers and normalization

Use one **2025/26 role cohort pooled across England, Spain, Germany, Italy and France**, not a player's league alone. Require 30 compatible peers and the current exposure requirement. Left/right counterparts share a cohort. GK has a separate population. LW/RW and LM/RM are separate roles, as are CM/CAM/CDM. Detailed role mappings must be reviewed; broad existing W/AM/DM labels cannot automatically establish every requested group.

Peers must share feature masks, effective weights, measurement definitions and season/window. Including both partial PitchAPI evidence and complete Opta evidence does not by itself make them comparable. Preserve identity confidence and do not double-count the same person's duplicated source rows. Mixed-position season production remains mixed unless role-specific minutes/events are actually available.

No league-strength multiplier is proposed. League/team context and intended style remain limitations until an evaluated adjustment exists.

1. Stabilize rates toward the compatible role mean: `x* = r × x + (1 − r) × μ`, `r = n / (n + k)`. Rate exposure uses minutes; success shares use attempts. Reuse the ST approach, but calibrate/version role-appropriate priors before release; the new weights do not imply validated shrinkage constants.
2. Compute the feature z-score against the compatible reference distribution. Multiply by `+1` or `−1` according to the documented direction.
3. Aggregate directional feature z-scores using effective within-ability weights.
4. Re-standardize each ability composite over the compatible peers.
5. Combine the six standardized abilities with the role's overall weights, then re-standardize that composite again.
6. Display each ability and OVR as `max(1, 50 + 15 × z)`. No upper cap; 50 is the reference mean before floor effects. Percentile is separate rank evidence, not the input to the score.

Zero reference variance cannot create a valid standardized ability. Withhold an unavailable ability or OVR rather than assign a fictional rating. Version the reference population, metrics, weights, effective masks, priors and scoring formula. Publish original values, exposure, contribution, coverage and reference distributions with the result.

## Zero-filled, actual zero and N/A

Only explicit **`unrecorded_zero`** inputs are removed from the parent ability and have their weights redistributed proportionally:

```text
effective_weight[j] = original_weight[j] / sum(original weights of retained features)
```

A recorded zero keeps its feature weight and participates normally. Example: `5:2:2:1`, with only the final feature zero-filled, becomes `5/9:2/9:2/9:0`. If the last value is an actual recorded zero, weights remain `5:2:2:1`.

An absent ratio input propagates its evidence status; it cannot become an observed ratio of zero. **Recorded zero attempts produce N/A**, not `unrecorded_zero`. Preserve N/A and invalid states and the existing eligibility rules; do not apply a blanket missing-value renormalization to them. A supported but undefined ratio is not a fabricated numeric performance observation.

If every feature in an ability is zero-filled, withhold that ability. Do not redistribute a missing parent's overall weight onto other parents. OVR requires all six calibrated abilities and a compatible common reference cohort. There is no new 90% or 70% availability gate in these proposals.

## What the scores can establish

These are transparent role-production composites, not validated predictions of transfer success or match impact. Correlated metrics do not become independent evidence just because their columns differ. Audit correlations, duplicated parent influence, weight sensitivity and stability before activating a registry.

Defensive actions need opportunity context. For now the proposals use documented per-90 production proxies; they do not claim possession adjustment. Add possession-adjusted or per-opportunity measures only when matching team/opposition exposure is available for the player's actual minutes. Whole-season team possession is not automatically that exposure.

Do not manufacture pace from carry distance, stamina from minutes, strength from body size, vision from completion, pressure resistance from low dispossessions, or GK reflexes/positioning from save volume. Describe these as missing scouting evidence. Footedness/side, age, identity and transfer constraints belong outside performance quality.

## Research and reproducibility

[EA's official attribute-family reference](https://media.contentapi.ea.com/content/dam/fifa/en-us/images-migrated/2018/09/chemistry-styles.pdf) supplies a game-facing grouping vocabulary, not Scout's coefficients. [Opta definitions](https://www.statsperform.com/opta-event-definitions/) distinguish passes, crosses, tackles, duels and recovery events. [StatsBomb's positional templates](https://blogarchive.statsbomb.com/articles/soccer/new-statsbomb-radars-2023-update/) motivate contextual interpretation rather than counting every action as pure quality.

Rebuild the eight drafts and inventory counts locally with:

```powershell
.venv/Scripts/python.exe tools/write_position_attribute_drafts.py
```

The tool reads SQLite in read-only mode, checks six parents and both levels of weight totals, verifies season-column inputs exist and reports raw appearance evidence. It writes review documents only. No full test suite, new crawl, rating recalculation or application release is needed for this documentation task.
