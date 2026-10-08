# Position weights and implementation

The engine loads [position_rating_weights_config.yaml](position_rating_weights_config.yaml). It contains ST, LW/RW, LM/RM, CM, CAM, CDM, CB, RB/LB and GK, each with six abilities, their feature weights and OVR weights. Left/right variants share a registry and reference cohort. The reviewed Markdown tables supplied the new position defaults; these remain provisional coefficients, not learned performance predictions.

## Tuning

Find the position under `positions`. Change `overall_weight` to alter an ability's contribution to OVR, or a value under that ability's `features` to alter its internal weighting. Values are fractions: `0.22` means 22%. Each position's six OVR weights and every ability's feature weights must independently sum to 1. Unknown features, duplicate YAML keys, non-finite weights and invalid totals fail validation.

For example, `positions.ST.abilities` now contains:

- Physicality: duels won 10%, duel success 30%, aerial wins 10%, aerial success 25%, dispossessed 25% (lower is better). Fouls won no longer contributes.
- Finishing: goals above non-penalty xG 30%, non-penalty xG 15%. The remaining finishing features share 55% proportionally (their previous ratio is preserved). CAM and LW/RW Scoring use the same 30%/15% pair.
- Link-Up / Creation: key passes 20%, completion 8%.
- Carrying / 1v1: take-on success 20%, successful take-ons 14%.

ST OVR weights are retained. Each parent totals 100%; the finishing correction scales its remaining feature weights proportionally.

After editing, rebuild from the workspace root:

```powershell
.venv/Scripts/python.exe -m scout.cli build-player-catalogue
```

Restart the local API when changing scoring configuration/code, then refresh the browser. Builds atomically activate a new private local catalogue; previous catalogues remain in the database. A snapshot stores its full configuration and SHA-256 checksum, feature/weighting versions, effective weights, source definitions and peer identities. Historical details use the saved configuration, rather than silently adopting subsequently edited weights. The installed wheel includes the configuration; a deployed override can use `SCOUT_POSITION_WEIGHTS_CONFIG`.

## Calculation

Provider-local measurements → exposure shrinkage → directional feature z-scores → weighted ability composite → ability standardization → six weighted abilities → OVR standardization. Display `max(1, 50 + 15 × z)`, without an upper cap. Percentile is separate rank evidence.

Minimum exposure is 900 minutes; minimum compatible cohort size is 30. Each position pools England, Spain, Germany, Italy and France. Cohorts retain the same provider definition and effective feature mask; a linked master identity is counted once. Goalkeepers never join outfield cohorts. The existing shrinkage priors are reused; additional success-rate attempts use a versioned provisional prior of 30 attempts.

Only `unrecorded_zero` features redistribute their weight proportionally within their ability. Actual recorded zeros retain their weights. Recorded zero-attempt ratios remain N/A; invalid and partial-window measurements do not become scored zeros. A wholly unavailable parent is not dropped from OVR. New-position zero-variance abilities remain unavailable. No arbitrary league-strength or coverage penalty is added.

### Squad assignments

Liverpool cards, substitution previews and details use the assigned slot's registry, including LM/RM separately from LW/RW. Every mapped Liverpool player has a frozen evaluation for each applicable position; goalkeeper and outfield assignments stay separate. Swaps change both OVR and the six ability names/features. The Players catalogue continues to show natural-position ratings.

Assigned-position reference players come from the destination's sourced natural position, pooled across all five leagues and deduplicated by corroborated master identity. References are recalculated using the subject's effective feature weights and compatible provider definitions. A removed zero-filled feature may be observed in a peer; that feature is excluded from both calculations. Moving players never changes reference membership. Each ability requires 30 compatible peers; OVR requires all six abilities and 30 aligned common peers. Frozen evaluations retain peer IDs, features, denominators and calibration evidence. Missing mappings, insufficient minutes, N/A, partial windows and undersized cohorts remain unavailable.

## Current data boundaries

Master input is the retained, read-only `data/master/2025-26-v2/master.sqlite`; source observations remain unchanged. Complete numerator/denominator bundles follow Opta → PitchAPI → Understat → WhoScored priority. Similarly named metrics with different scopes are not silently substituted. Keeper appearances are deduplicated by provider player and sample, percentages are exposure-weighted, and matched minutes are retained. A keeper appearance window differing materially from the season exposure is explicitly partial and cannot supply a complete season rating.

Broad source labels map W→LW/RW, AM→CAM, DM→CDM and FB/WB→RB/LB. LM/RM requires explicit wide-midfielder reference evidence; the current source labels contain no verified LM/RM cohort. Squad cards show assigned-position abilities, with unavailable scores where that registry lacks adequate evidence. Out-of-natural-position assignments are evaluated without an arbitrary penalty; the score does not certify tactical suitability. Five Liverpool identities remain unmapped. Historical performance-season clubs and current squad membership remain separate.

## Verification and local results

The rebuild scored 1,216 overall ratings: ST 158, LW/RW 152, CM 172, CAM 72, CDM 75, CB 292, RB/LB 262 and GK 33. LM/RM has zero eligible records. The catalogue retains 4,308 source/corroborated profiles, including unresolved identity copies; this is not a unique-person claim.

Forty focused Python checks cover historical calibration parity, all nine model registries, pooled cohorts, GK separation, missingness, recorded zeros, zero-attempt N/A, partial windows, signed measurements, YAML validation and keeper sample deduplication. The frontend build and shared card/filter checks pass. Cards and radar/distribution details use position-specific abilities. Recruitment publication and source permissions are unchanged; Understat remains private.

The assigned-position follow-up passed 38 targeted Python checks, 13 frontend checks and a production build. A real-data ST↔CM swap changed Ekitike's six abilities and OVR; evaluation, player details and substitution preview agreed. Desktop and mobile inspections verified Mac Allister's CM card and CM ability analysis. Default-lineup midfield scores are Mac Allister CM 42.8, Gravenberch CDM 62.3 and Szoboszlai CM 67.8. Isak remains unavailable at 703 minutes.
