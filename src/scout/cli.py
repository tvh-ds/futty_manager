import json
from pathlib import Path

import typer

from scout.database import Base, connect
from scout.demo import demonstration
from scout.engine import RecruitmentEngine
from scout.evaluation import brief_suite, evaluate
from scout.ingestion import ApiFootball, QuotaExhausted, canonicalize
from scout.lakehouse import build_local, build_spark
from scout.releases import publish, read_bundle, rollback, write_bundle
from scout.settings import Settings

app = typer.Typer(no_args_is_help=True)


@app.command("reprocess-opta")
def reprocess_opta(source: Path, destination: Path):
    """Normalize cached Opta bronze, including the separate goalkeeper report."""
    from scout.opta_analyst_probe import reprocess
    report = reprocess(source, destination)
    typer.echo(json.dumps({"players": sum(v['players'] for v in report['leagues'].values()),
                           "output": str(destination), "network_requests": 0}, indent=2))


@app.command("build-player-catalogue")
def build_player_catalogue(pitchapi: Path = Path("data/pitchapi/live-probe-2025"),
                           output: Path = Path("data/real-data/catalogue-report.json")):
    """Map real identities, extract sourced portraits and calibrate strict abilities."""
    from scout.player_catalogue import build_catalogue
    database = connect(Settings().database_url)
    try:
        report = build_catalogue(database, pitchapi)
        write_json(output, report)
    except (OSError, ValueError, TypeError, KeyError) as error:
        typer.echo(f"Catalogue build refused: {type(error).__name__}: {error}", err=True)
        raise typer.Exit(1) from None
    finally:
        database.dispose()
    typer.echo(json.dumps({key: report[key] for key in (
        "catalogue_id", "total", "linked_source_records", "portraits", "rated_overall", "unmapped_squad_players")}, indent=2))


@app.command("import-real-data")
def import_real_data(pitchapi: Path, opta: Path, understat: Path,
                     output: Path = Path("data/real-data/import-report.json"),
                     identities: Path | None = None):
    """Load collected 2025/26 evidence atomically; never publishes a candidate release.

    Run alembic upgrade head first. Optional identities is a documented review
    list, not an automatically accepted name matching file.
    """
    from sqlalchemy import inspect

    from scout.real_data import import_evidence
    database = connect(Settings().database_url)
    try:
        if "evidence_imports" not in inspect(database).get_table_names():
            raise ValueError("Database needs alembic upgrade head before import")
        report = import_evidence(database, {"pitchapi": pitchapi, "opta": opta, "understat": understat}, identities)
        write_json(output, report)
    except (OSError, ValueError, TypeError, KeyError) as error:
        typer.echo(f"Real evidence import refused: {type(error).__name__}: {error}", err=True)
        raise typer.Exit(1) from None
    finally:
        database.dispose()
    typer.echo(json.dumps({key: report[key] for key in (
        "id", "records", "source_counts", "feature_observations", "reviewed_links", "publication_approved")}, indent=2))


@app.command("audit-pitchapi")
def audit_pitchapi(source: Path, output: Path, threshold: float = 90.0):
    """Audit real feature coverage without fetching, imputing or publishing data."""
    from scout.pitchapi import strict_json
    from scout.pitchapi_coverage import audit
    try:
        if source.stat().st_size > 200_000_000:
            raise ValueError('Oversized measurement file')
        rows = strict_json(source.read_bytes())
        if not isinstance(rows, list) or len(rows) > 10000:
            raise ValueError('Invalid measurement rows')
        report = audit(rows, threshold)
        write_json(output, report)
    except (OSError, ValueError, TypeError, KeyError):
        typer.echo('Coverage audit input invalid.', err=True)
        raise typer.Exit(1) from None
    typer.echo(json.dumps({'players': report['all_players']['players'],
        'threshold_pct': threshold, 'accepted_features': report['all_players']['accepted_features'],
        'all_features_accepted': report['all_players']['all_features_accepted'], 'report': str(output)}, indent=2))


@app.command("collect-pitchapi")
def collect_pitchapi(output: Path = Path("data/pitchapi/2025"), season: int = 2025,
                     max_requests: int = 200, matches_per_league: int | None = None):
    """Collect resumable private evidence. Samples never activate player ratings."""
    from scout.pitchapi import collect
    key = Settings().pitchapi_key.get_secret_value()
    if not key:
        typer.echo("SCOUT_PITCHAPI_KEY is empty; save it in .env.", err=True)
        raise typer.Exit(1)
    try:
        _, report = collect(output, key, season, max_requests, matches_per_league)
    except (OSError, ValueError, TypeError):
        typer.echo("PitchAPI collection configuration invalid.", err=True)
        raise typer.Exit(1) from None
    typer.echo(json.dumps(report, indent=2))
    if report.get("failure"):
        raise typer.Exit(1)


@app.command("probe-understat")
def probe_understat(output: Path, season: int = 2026):
    """One-off private numeric coverage probe; never publishes or schedules."""
    from scout.understat_probe import probe
    report = probe(output, season)
    typer.echo(json.dumps(report, indent=2))
    if any('failure' in value for value in report['leagues'].values()):
        raise typer.Exit(1)


@app.command("probe-understat-player")
def probe_understat_player(output: Path, league_snapshot: Path, player_id: str,
                          competition: str = 'England', season: int = 2025):
    """Reconcile one player's real shots against a private league snapshot."""
    from scout.understat_probe import probe_player
    row = probe_player(output, league_snapshot, player_id, competition, season)
    typer.echo(json.dumps({'player_id': player_id, 'season': row['season'],
        'shot_count': row['shot_count'], 'available_features': sum(v is not None for v in row['features'].values()),
        'publication_approved': False, 'activated': False}, indent=2))


@app.command("refresh-strikers")
def refresh_strikers(import_path: Path | None = None, config_path: Path = Path("config/striker-source.json"),
                     pitchapi_cache: Path | None = None):
    """Monthly numeric refresh. No live source is enabled by default."""
    from scout.striker_refresh import refresh
    report = refresh(import_path=import_path, config_path=config_path, pitchapi_cache=pitchapi_cache)
    typer.echo(json.dumps(report, indent=2))
    if report.get("failure"):
        raise typer.Exit(1)


@app.command("reproduce-strikers")
def reproduce_strikers(source: Path, destination: Path):
    """Verify a striker release offline without activation or cloud access."""
    from scout.striker_refresh import reproduce_release
    try:
        report = reproduce_release(source, destination)
    except (OSError, ValueError, KeyError, TypeError) as error:
        typer.echo(f"Striker reproduction refused: {type(error).__name__}", err=True)
        raise typer.Exit(1) from None
    typer.echo(json.dumps(report, indent=2))


@app.command("striker-state")
def striker_state(action: str, account: str, allow_empty: bool = False):
    """Restore/save monthly runner state in an existing private Azure container."""
    from scout.striker_state import private_container, restore_cloud, save_cloud
    if action not in {"restore", "save"}:
        raise typer.BadParameter("Action must be restore or save")
    token = Path(".cache/striker-cloud-generation.json")
    container = private_container(account)
    if action == "restore":
        result = restore_cloud(Path("data/strikers"), container)
        if not result["restored"] and not allow_empty:
            raise typer.BadParameter("Private state pointer missing; explicit --allow-empty required for bootstrap")
        write_json(token, {"account": account, "etag": result["etag"]})
    else:
        if not token.exists():
            raise typer.BadParameter("Restore private state before saving")
        generation = json.loads(token.read_text())
        if generation.get("account") != account:
            raise typer.BadParameter("Private state account changed")
        result = save_cloud(Path("data/strikers"), container, generation["etag"])
    typer.echo(json.dumps(result, indent=2))


def write_json(path: Path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, default=str), encoding="utf-8")


@app.command("demo")
def demo(engine: str = "local"):
    settings = Settings()
    release, players, teams = demonstration()
    path = settings.release_root / release.id / "bundle.json"
    if path.exists():
        release, players, teams, _ = read_bundle(path)
    else:
        path = write_bundle(settings.release_root, release, players, teams)
    database = connect(settings.database_url)
    Base.metadata.create_all(database)
    build_spark(Path("data/lakehouse"), release, players, teams) if engine == "spark" else build_local(Path("data/lakehouse"), release, players, teams)
    publish(database, path)
    recruitment = RecruitmentEngine(release, players, teams)
    cases = brief_suite(recruitment)
    write_json(Path("artifacts/evaluation/briefs.json"), cases)
    write_json(Path("artifacts/evaluation/report.json"), evaluate(recruitment, cases))
    typer.echo(f"Published {release.id}: {len(players)} fictional player stints, eight roles, ten fictional clubs")


@app.command("probe")
def probe(season: int = 2024):
    settings = Settings()
    report = ApiFootball(settings.api_football_key, Path("data/raw/api-football")).probe(season)
    write_json(Path("artifacts/coverage/api-football.json"), report)
    typer.echo("Coverage report written. Public display approval remains unverified.")


@app.command("ingest")
def ingest(season: int = 2024):
    settings = Settings()
    try:
        ApiFootball(settings.api_football_key, Path("data/raw/api-football")).ingest(season)
    except QuotaExhausted as error:
        typer.echo(str(error))
        raise typer.Exit(75) from None


@app.command("build")
def build(release_id: str, season: int = 2024, overrides: Path = Path("config/role-overrides.json"),
          permission: Path = Path("config/publication.json"), engine: str = "local"):
    from scout.contracts import DatasetRelease
    from scout.roles import TOP_FIVE
    approval = json.loads(permission.read_text(encoding="utf-8"))
    if not approval.get("approved") or not approval.get("evidence"):
        raise typer.BadParameter("Record source-specific public display permission before building a real release")
    players, teams, quarantine = canonicalize(Path("data/raw/api-football"), season,
                                              json.loads(overrides.read_text(encoding="utf-8")))
    write_json(Path("artifacts/coverage/quarantine.json"), quarantine)
    release = DatasetRelease(id=release_id, kind="real", season=f"{season}/{str(season + 1)[-2:]}",
        leagues=list(TOP_FIVE), source="API-Football", publication_approved=True,
        publication_evidence=approval["evidence"], limitations=["Detailed outfield roles use reviewed manual overrides",
        "Only unambiguous count fields are normalized; age at season and rich tactical attributes are unknown",
        "Save share does not adjust for shot difficulty; tactical coverage is sparse"])
    path = write_bundle(Settings().release_root, release, players, teams)
    build_spark(Path("data/lakehouse"), release, players, teams) if engine == "spark" else build_local(Path("data/lakehouse"), release, players, teams)
    typer.echo(str(path))


@app.command("publish")
def publish_release(bundle: Path):
    database = connect(Settings().database_url)
    typer.echo(publish(database, bundle))


@app.command("rollback")
def rollback_release(release_id: str):
    rollback(connect(Settings().database_url), release_id)
    typer.echo(f"Restored {release_id}; API reloads on the next request")


@app.command("evaluate")
def evaluate_release(bundle: Path, judgments: Path | None = None):
    release, players, teams, _ = read_bundle(bundle)
    engine = RecruitmentEngine(release, players, teams)
    cases = json.loads(judgments.read_text()) if judgments else brief_suite(engine)
    write_json(Path("artifacts/evaluation/report.json"), evaluate(engine, cases))


@app.command("openapi")
def openapi(output: Path = Path("frontend/openapi.json")):
    # Export every frontend contract regardless of local serving permissions.
    # This creates a schema-only app; it does not enable private endpoints on
    # the running API or publish any imported evidence.
    from scout.api import create_app
    write_json(output, create_app(Settings(serve_private_evidence=True)).openapi())


@app.command("train-xg")
def train_xg(shots: Path, output: Path = Path("artifacts/xg"), pytorch: bool = False):
    from scout.models.xg import train
    train(shots, output, pytorch=pytorch)


@app.command("historical-shots")
def historical_shots(root: Path = Path("data/historical/statsbomb"), competition: int = 9, season: int = 281):
    from scout.historical import fetch_research
    typer.echo(str(fetch_research(root, competition, season)))


@app.command("train-xt")
def train_xt(root: Path = Path("data/historical/statsbomb"), output: Path = Path("artifacts/xt")):
    from scout.models.action_value import train_xt as train
    train(root, output)


@app.command("register-research")
def register_research(card: Path = Path("artifacts/xg/model-card.json")):
    from scout.models.xg import register_research as register
    register(card)
    typer.echo("Registered historical research versions; candidate promotion remains unapproved")


@app.command("cloud-transfer")
def cloud_transfer(local: Path, volume: str, download: bool = False):
    from scout.cloud import transfer_volume
    transfer_volume(local, volume, download)


@app.command("probe-opta-analyst")
def probe_opta_analyst(output: Path, season: int = 2025):
    """Collect public Opta feeds and audit coverage without activating ratings."""
    from scout.opta_analyst_probe import probe
    try:
        report = probe(output, season)
    except (ValueError, FileExistsError) as error:
        raise typer.BadParameter(str(error)) from None
    typer.echo(json.dumps({'requested_season': report['requested_season'],
        'requested_window_available': report['requested_window_available'],
        'inventory_rows': report['coverage']['all_players']['players'],
        'features_passing_90_pct': report['coverage']['all_players']['accepted_features'],
        'appearance_rows': report['appearance_coverage']['all_players']['players'],
        'appearance_features_passing_90_pct': report['appearance_coverage']['all_players']['accepted_features'],
        'activated': False, 'report': str(output / 'coverage.json')}, indent=2))


@app.command("audit-data-sources")
def audit_data_sources(fetch: bool = False):
    """Inventory all cached raw fields and compare source combinations; no publication."""
    from scout.source_audit import run
    typer.echo(json.dumps(run(fetch=fetch), indent=2))


@app.command("collect-source-tables")
def collect_source_tables(budget: int = typer.Option(160, min=1, max=300)):
    """Resume bounded public navigation/table collection; never publish data."""
    from scout.source_site_probe import collect, seasons
    seasons()
    typer.echo(json.dumps(collect(budget=budget), indent=2))


@app.command("merge-master-data")
def merge_master_data(output: Path = Path('data/master/2025-26'), resume_observations: Path | None = None):
    """Merge four cached sources into a private master; preserve conflicts and provenance."""
    from scout.master_dataset import build
    try:
        report = build(output, resume_observations=resume_observations)
        from scout.master_export import export_named
        export_named(output)
        from scout.master_identity import merge_names
        output = Path(merge_names(output)['revision_path'])
        from scout.master_missing import fill_missing
        output = Path(fill_missing(output)['revision_path'])
        report = json.loads((output / 'manifest.json').read_text(encoding='utf-8'))
    except (ValueError, FileExistsError) as error:
        raise typer.BadParameter(str(error)) from None
    typer.echo(json.dumps({'revision_path': str(output), **{key: report[key] for key in (
        'version', 'sources', 'master_rows', 'input_numeric_columns', 'master_numeric_columns', 'cell_status')}}, indent=2))


@app.command('resolve-master-conflicts')
def resolve_master_conflicts(folder: Path = Path('data/master/2025-26-v2')):
    """Apply Opta > PitchAPI > Understat > WhoScored to master conflicts."""
    from scout.master_priority import resolve_master
    typer.echo(json.dumps(resolve_master(folder), indent=2))


@app.command('deduplicate-master-players')
def deduplicate_master_players(folder: Path = Path('data/master/2025-26-v2')):
    """Merge same-name/same-league rows; select overlapping features by source priority."""
    from scout.master_identity import merge_names
    typer.echo(json.dumps(merge_names(folder), indent=2))


@app.command('zero-fill-master-values')
def zero_fill_master_values(folder: Path = Path('data/master/2025-26-v2')):
    """Label unrecorded master numeric values 0 after merging sources."""
    from scout.master_missing import fill_missing
    typer.echo(json.dumps(fill_missing(folder), indent=2))


if __name__ == "__main__":
    app()
