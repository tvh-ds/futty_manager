import hashlib
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score
from sklearn.mixture import GaussianMixture
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

FEATURES = ["distance", "angle", "header", "under_pressure"]


def metrics(labels, probabilities):
    labels, probabilities = np.asarray(labels), np.asarray(probabilities)
    bins = np.linspace(0, 1, 11)
    calibration = []
    for index in range(10):
        selected = (probabilities >= bins[index]) & (probabilities < bins[index + 1] if index < 9 else probabilities <= 1)
        if selected.any():
            calibration.append({"count": int(selected.sum()), "predicted": float(probabilities[selected].mean()),
                                "observed": float(labels[selected].mean())})
    return {"brier": float(brier_score_loss(labels, probabilities)),
            "log_loss": float(log_loss(labels, probabilities, labels=[0, 1])),
            "roc_auc": float(roc_auc_score(labels, probabilities)) if len(np.unique(labels)) > 1 else None,
            "calibration": calibration}


def chronological_split(frame):
    required = {"match_id", "match_date", "goal", *FEATURES}
    if not required.issubset(frame.columns):
        raise ValueError(f"Required shot columns: {sorted(required)}")
    if frame["match_id"].isna().any() or not frame["goal"].isin([0, 1]).all():
        raise ValueError("Match IDs and binary shot outcomes are required")
    dates = pd.to_datetime(frame["match_date"], utc=True, errors="raise")
    if dates.isna().any():
        raise ValueError("Missing match dates")
    ordered = frame.assign(match_date=dates).groupby("match_id")["match_date"].agg(["min", "max"])
    if (ordered["min"] != ordered["max"]).any():
        raise ValueError("A match cannot span date folds")
    ordered = ordered.sort_values(["min"])
    if len(ordered) < 20:
        raise ValueError("At least 20 dated matches are required for train/validation/test")
    dates_unique = sorted(ordered["min"].unique())
    if len(dates_unique) < 5:
        raise ValueError("At least five distinct match dates are required")
    train_cut = dates_unique[max(0, int(len(dates_unique) * 0.6) - 1)]
    valid_cut = dates_unique[max(1, int(len(dates_unique) * 0.8) - 1)]
    train = frame.loc[dates <= train_cut]
    validation = frame.loc[(dates > train_cut) & (dates <= valid_cut)]
    test = frame.loc[dates > valid_cut]
    if any(part.empty or part["goal"].nunique() < 2 for part in (train, validation, test)):
        raise ValueError("Every chronological fold needs both outcome classes")
    return train, validation, test


def fit_torch(train, validation, test):
    import torch
    torch.manual_seed(42)
    torch.set_num_threads(2)
    preprocessing = make_pipeline(SimpleImputer(strategy="median"), StandardScaler())
    x_train = torch.tensor(preprocessing.fit_transform(train[FEATURES]), dtype=torch.float32)
    labels = torch.tensor(train.goal.to_numpy(), dtype=torch.float32).reshape(-1, 1)
    x_validation = torch.tensor(preprocessing.transform(validation[FEATURES]), dtype=torch.float32)
    model = torch.nn.Sequential(torch.nn.Linear(4, 16), torch.nn.ReLU(), torch.nn.Linear(16, 8),
                                torch.nn.ReLU(), torch.nn.Linear(8, 1))
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    best_loss, best_state = float("inf"), None
    loss_fn = torch.nn.BCEWithLogitsLoss()
    for _ in range(80):
        model.train()
        optimizer.zero_grad()
        loss_fn(model(x_train), labels).backward()
        optimizer.step()
        model.eval()
        with torch.no_grad():
            probabilities = torch.sigmoid(model(x_validation)).numpy().ravel()
        loss = log_loss(validation.goal, probabilities, labels=[0, 1])
        if loss < best_loss:
            best_loss = loss
            best_state = {key: value.detach().clone() for key, value in model.state_dict().items()}
    model.load_state_dict(best_state)
    with torch.no_grad():
        validation_predictions = torch.sigmoid(model(x_validation)).numpy().ravel()
        test_predictions = torch.sigmoid(model(torch.tensor(preprocessing.transform(test[FEATURES]), dtype=torch.float32))).numpy().ravel()
    return model, preprocessing, validation_predictions, test_predictions


def train(shots: Path, output: Path, pytorch: bool = False):
    import mlflow
    import mlflow.catboost
    import mlflow.sklearn
    from catboost import CatBoostClassifier
    frame = pd.read_parquet(shots) if shots.suffix == ".parquet" else pd.read_csv(shots)
    frame[FEATURES] = frame[FEATURES].astype(float)
    train_frame, validation, test = chronological_split(frame)
    output.mkdir(parents=True, exist_ok=True)
    mlflow.set_experiment("scout-historical-xg")
    dataset_hash = hashlib.sha256(shots.read_bytes()).hexdigest()
    candidates = {
        "logistic": make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), LogisticRegression(random_state=42)),
        "catboost": make_pipeline(SimpleImputer(strategy="median"), CatBoostClassifier(
            iterations=120, depth=4, learning_rate=0.05, random_seed=42, thread_count=2, verbose=False)),
    }
    report = {"dataset_sha256": dataset_hash, "scope": "Historical shot outcomes; not current player quality or transfer prediction",
              "split": "Chronological dates with whole matches; preprocessing fitted only to training",
              "rows": {"train": len(train_frame), "validation": len(validation), "test": len(test)},
              "models": {}}
    validation_scores = {}
    for name, model in candidates.items():
        started = time.monotonic()
        model.fit(train_frame[FEATURES], train_frame.goal)
        validation_predictions = model.predict_proba(validation[FEATURES])[:, 1]
        test_predictions = model.predict_proba(test[FEATURES])[:, 1]
        results = {"validation": metrics(validation.goal, validation_predictions), "test": metrics(test.goal, test_predictions),
                   "training_seconds": time.monotonic() - started}
        validation_scores[name] = results["validation"]["brier"]
        with mlflow.start_run(run_name=name) as run:
            mlflow.log_params({"seed": 42, "dataset_sha256": dataset_hash, "features": ",".join(FEATURES), "scope": "historical"})
            mlflow.log_input(mlflow.data.from_pandas(train_frame, targets="goal", name="train"), context="training")
            mlflow.log_metrics({"test_brier": results["test"]["brier"], "validation_brier": results["validation"]["brier"],
                                "training_seconds": results["training_seconds"]})
            if name == "logistic":
                info = mlflow.sklearn.log_model(model, name="model", input_example=train_frame[FEATURES].head(2),
                    pyfunc_predict_fn="predict_proba", skops_trusted_types=["numpy.dtype"])
                restored = mlflow.sklearn.load_model(info.model_uri)
                restored_predictions = restored.predict_proba(test[FEATURES])[:, 1]
            else:
                preprocessing_info = mlflow.sklearn.log_model(model[0], name="preprocessing", input_example=train_frame[FEATURES].head(2),
                                        pyfunc_predict_fn="transform",
                                        skops_trusted_types=["numpy.dtype"])
                info = mlflow.catboost.log_model(model[1], name="model", input_example=model[0].transform(train_frame[FEATURES].head(2)))
                restored_preprocessing = mlflow.sklearn.load_model(preprocessing_info.model_uri)
                restored = mlflow.catboost.load_model(info.model_uri)
                restored_predictions = restored.predict_proba(restored_preprocessing.transform(test[FEATURES]))[:, 1]
                results["preprocessing_uri"] = preprocessing_info.model_uri
                results["inference"] = "Apply stored median preprocessing, then native CatBoost predict_proba[:,1]"
            results["model_uri"] = info.model_uri
            results["artifact_reload_max_error"] = float(np.max(np.abs(restored_predictions - test_predictions)))
            if results["artifact_reload_max_error"] > 1e-6:
                raise ValueError("Model artifact reproduction failed")
            mlflow.log_dict(results, "evaluation.json")
            results["run_id"] = run.info.run_id
        report["models"][name] = results
    if pytorch:
        import mlflow.pytorch
        import torch
        started = time.monotonic()
        model, preprocessing, validation_predictions, test_predictions = fit_torch(train_frame, validation, test)
        training_seconds = time.monotonic() - started
        with mlflow.start_run(run_name="pytorch-mlp") as run:
            results = {"validation": metrics(validation.goal, validation_predictions), "test": metrics(test.goal, test_predictions),
                       "run_id": run.info.run_id, "training_seconds": training_seconds}
            mlflow.log_params({"seed": 42, "dataset_sha256": dataset_hash, "epochs": 80, "architecture": "4-16-8-1"})
            mlflow.log_metrics({"test_brier": results["test"]["brier"], "validation_brier": results["validation"]["brier"]})
            example = preprocessing.transform(train_frame[FEATURES].head(2)).astype(np.float32)
            probability_model = torch.nn.Sequential(model, torch.nn.Sigmoid()).eval()
            info = mlflow.pytorch.log_model(probability_model, name="model", input_example=example)
            preprocessing_info = mlflow.sklearn.log_model(preprocessing, name="preprocessing", input_example=train_frame[FEATURES].head(2),
                                    pyfunc_predict_fn="transform",
                                    skops_trusted_types=["numpy.dtype"])
            restored = mlflow.pytorch.load_model(info.model_uri)
            restored_preprocessing = mlflow.sklearn.load_model(preprocessing_info.model_uri)
            with torch.no_grad():
                restored_predictions = restored(torch.tensor(restored_preprocessing.transform(test[FEATURES]), dtype=torch.float32)).numpy().ravel()
            results["model_uri"] = info.model_uri
            results["preprocessing_uri"] = preprocessing_info.model_uri
            results["artifact_reload_max_error"] = float(np.max(np.abs(restored_predictions - test_predictions)))
            if results["artifact_reload_max_error"] > 1e-6:
                raise ValueError("PyTorch artifact reproduction failed")
            mlflow.log_dict(results, "evaluation.json")
            report["models"]["pytorch"] = results
            validation_scores["pytorch"] = results["validation"]["brier"]
    baseline = validation_scores["logistic"]
    best = min(validation_scores, key=validation_scores.get)
    report["selected_on_validation"] = best if validation_scores[best] < baseline - 0.002 else "logistic"
    report["promotion"] = "Research only. No candidate-release promotion without a separate held-out acceptance review."
    (output / "model-card.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def archetypes(matrix: np.ndarray, components: int = 3):
    from sklearn.decomposition import PCA
    if len(matrix) < components * 10:
        raise ValueError("Insufficient role examples for stable archetypes")
    pipeline = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                             PCA(n_components=min(3, matrix.shape[1])),
                             GaussianMixture(n_components=components, random_state=42))
    return pipeline.fit(matrix)


def register_research(card: Path):
    import re

    import mlflow

    report = json.loads(card.read_text())
    if report.get("scope") != "Historical shot outcomes; not current player quality or transfer prediction":
        raise ValueError("Only historical shot research can use this registry command")
    client = mlflow.MlflowClient()
    for name, result in report["models"].items():
        if name not in {"logistic", "catboost", "pytorch"} or not re.fullmatch(r"models:/m-[a-f0-9]+", result["model_uri"]):
            raise ValueError("Unsupported research model or artifact URI")
        if result.get("artifact_reload_max_error", float("inf")) > 1e-6:
            raise ValueError("Reload validation required before research registration")
        version = mlflow.register_model(result["model_uri"], "scout-historical-xg-" + name)
        client.set_model_version_tag(version.name, version.version, "scope", "historical-research-only")
        client.set_model_version_tag(version.name, version.version, "candidate_release_promotion", "not-approved")
        result["registered_version"] = version.version
    card.write_text(json.dumps(report, indent=2))
