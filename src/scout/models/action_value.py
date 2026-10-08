"""Reference socceraction xT on chronologically held-out historical matches."""
import json
from pathlib import Path

import numpy as np
import pandas as pd


def train_xt(root: Path, output: Path):
    import mlflow
    import socceraction.spadl as spadl
    from socceraction.data.statsbomb import StatsBombLoader
    from socceraction.xthreat import ExpectedThreat

    manifest = json.loads((root / "source-manifest.json").read_text())
    selection = manifest["competition"]
    loader = StatsBombLoader(getter="local", root=str(root / manifest["revision"] / "data"))
    games = loader.games(selection["competition_id"], selection["season_id"]).sort_values("game_date")
    dates = sorted(games.game_date.unique())
    if len(dates) < 5 or len(games) < 20:
        raise ValueError("At least 20 matches and five dates required for historical xT")
    cut = dates[max(0, int(len(dates) * 0.8) - 1)]
    training, heldout = [], []
    for game in games.itertuples():
        events = loader.events(game.game_id)
        events = events.loc[events.period_id < 5]
        actions = spadl.statsbomb.convert_to_actions(events, home_team_id=game.home_team_id)
        actions = spadl.play_left_to_right(actions, game.home_team_id)
        (training if game.game_date <= cut else heldout).append(actions)
    training, heldout = pd.concat(training, ignore_index=True), pd.concat(heldout, ignore_index=True)
    model = ExpectedThreat(l=16, w=12)
    model.fit(training)
    values = model.rate(heldout)
    valid = values[np.isfinite(values)]
    output.mkdir(parents=True, exist_ok=True)
    model.save_model(str(output / "xt-grid.json"))
    report = {"source_revision": manifest["revision"], "scope": "historical-research-only",
        "method": "socceraction ExpectedThreat 16x12; chronological train/test with whole matches",
        "train_actions": len(training), "test_actions": len(heldout), "scored_test_actions": len(valid),
        "mean_test_action_value": float(valid.mean()) if len(valid) else None,
        "limitations": ["Descriptive held-out action-value distribution, not predictive accuracy or validated ranking relevance",
                        "xT values successful ball movements; no defensive/off-ball player quality claim",
                        "Small biased open-match selection; no current candidate promotion"]}
    (output / "model-card.json").write_text(json.dumps(report, indent=2))
    mlflow.set_experiment("scout-historical-action-value")
    with mlflow.start_run(run_name="reference-xt"):
        mlflow.log_params({"grid": "16x12", "source_revision": manifest["revision"], "scope": "historical"})
        mlflow.log_metrics({"train_actions": len(training), "test_actions": len(heldout), "scored_test_actions": len(valid)})
        mlflow.log_artifacts(str(output))
    return report
