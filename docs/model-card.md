# Historical research model card — 2026-10-06

## Scope and data

Personal research experiments on [StatsBomb Open Data](https://github.com/hudl/open-data), archived revision `4b73468fc5b0f1950f9f66fada70ad3a4f9327cb`. The selected 34 men's Bundesliga 2023/24 matches yielded 916 valid shots. This sample is biased toward the available open matches. It does not calibrate top-five-league player quality, tactical fit, transfer outcomes or current candidates.

Shot features: normalized-pitch distance and angle, header indicator, provider pressure flag. No provider xG value or post-shot location enters training. In-match penalties are retained; shootouts excluded. Chronological whole-date/whole-match folds contain 534 training, 192 validation and 190 test shots. Preprocessing fits only training; neural checkpoints use validation loss. Test labels never choose the winning model.

## Observed local benchmark

| Model | Validation Brier ↓ | Test Brier ↓ | Training seconds* |
|---|---:|---:|---:|
| Logistic regression | 0.081635 | 0.112729 | 0.047 |
| CatBoost, 120 iterations / depth 4 | 0.084736 | 0.113626 | 0.234 |
| PyTorch MLP, 4–16–8–1 / up to 80 epochs | 0.081425 | 0.110901 | 1.594 |

*One small-data CPU run; excludes import/MLflow serialization costs. These are execution observations, not performance guarantees or repeated-trial confidence intervals.* Full log-loss, ROC AUC and calibration bins are in ignored `artifacts/xg/model-card.json`, together with checksums, run IDs, model URIs and saved-model reload results. All three reloads reproduced test probabilities with maximum absolute difference zero in the tested environment.

Logistic remains selected: the neural validation Brier improvement was approximately 0.00021, below the configured 0.002 improvement threshold. This threshold is a conservative engineering rule, not a statistical significance test. CatBoost performed worse on validation. Neither complex experiment is promoted into candidate ranking. Report small-sample uncertainty and repeated chronological backtests before making football conclusions.

MLflow records dataset hashes, seeds, training inputs, metrics and input/output schemas (model signatures). Classical preprocessors use skops with a narrow `numpy.dtype` allowlist. CatBoost uses its native model format with a separate stored median imputer. PyTorch uses an exported probability model and separate trained preprocessing. Artifacts remain private/local; do not load arbitrary untrusted model files. All three have local registered research version 1, tagged as unapproved for candidate promotion.

## Action-value reference

The socceraction 16×12 xT reference fit 64,627 historical actions, then scored 12,679 successful movements among 15,586 chronologically held-out actions. Mean held-out movement value: 0.001215. This distribution is **not an accuracy/relevance score**. xT describes changes in a grid's estimated scoring threat; it does not value off-ball defending or establish whole-player quality. Grid and source/run details are in `artifacts/xt/` and local MLflow. The upstream JSON/SPADL path emits pandas compatibility warnings; regression verification is required when dependencies change.

## Remaining research acceptance

Bootstrap match-level confidence intervals, richer baselines, subgroup calibration, archetype stability, human judgments on the 32 held-out recruitment briefs and VAEP are still needed. No external reviewer has endorsed recommendations. Cloud registration and model-release acceptance require separate verification; no cloud training/registry result is claimed.
