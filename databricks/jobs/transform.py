"""Thin serverless job. No live provider requests, serving DB access or ADLS mounts."""
import argparse
import json
from pathlib import Path

from scout.lakehouse import build_spark
from scout.releases import read_bundle, write_bundle


def main():
    from databricks.connect import DatabricksSession

    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    release, players, teams, checksum = read_bundle(args.bundle)
    spark = DatabricksSession.builder.getOrCreate()
    result = build_spark(args.output, release, players, teams, spark=spark, catalog=args.catalog)
    output = write_bundle(args.output, release, players, teams)
    result["input_sha256"] = checksum
    (output.parent / "pipeline-report.json").write_text(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
