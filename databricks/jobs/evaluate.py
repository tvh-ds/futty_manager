import argparse
import json
from pathlib import Path

from scout.engine import RecruitmentEngine
from scout.evaluation import brief_suite, evaluate
from scout.releases import read_bundle


def main():
    import mlflow

    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args()
    release, players, teams, checksum = read_bundle(args.bundle)
    engine = RecruitmentEngine(release, players, teams)
    cases = brief_suite(engine)
    report = evaluate(engine, cases)
    path = args.bundle.parent / "evaluation.json"
    path.write_text(json.dumps(report, indent=2))
    mlflow.set_experiment("/Users/" + __import__("databricks.sdk", fromlist=["WorkspaceClient"]).WorkspaceClient().current_user.me().user_name + "/scout-role-baseline")
    with mlflow.start_run(run_name=release.id):
        mlflow.log_params({"release_id": release.id, "bundle_sha256": checksum,
                           "feature_version": release.feature_version, "scoring_version": release.scoring_version,
                           "data_kind": release.kind, "players": len(players), "briefs": len(cases)})
        mlflow.log_artifact(str(path))
        mlflow.set_tag("judgments", "unreviewed-personal-assessment; no certified relevance")


if __name__ == "__main__":
    main()
