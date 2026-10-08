import numpy as np
import pytest

pd = pytest.importorskip("pandas")
from scout.models.xg import chronological_split, metrics  # noqa: E402


def test_split_is_chronological_and_whole_match():
    frame = pd.DataFrame([{"match_id": day, "match_date": f"2023-01-{day:02}", "goal": goal,
                           "distance": 10, "angle": 0.5, "header": 0, "under_pressure": 0}
                          for day in range(1, 26) for goal in (0, 1)])
    train, validation, test = chronological_split(frame)
    assert train.match_date.max() < validation.match_date.min() < test.match_date.min()
    assert not set(train.match_id) & set(validation.match_id) & set(test.match_id)
    frame.loc[1, "match_date"] = "2023-02-01"
    with pytest.raises(ValueError, match="date folds"):
        chronological_split(frame)


def test_calibration_and_single_class_metrics_are_defined():
    result = metrics(np.zeros(4), np.full(4, 0.2))
    assert result["roc_auc"] is None
    assert result["brier"] == pytest.approx(0.04)
    assert sum(bin["count"] for bin in result["calibration"]) == 4
