import json

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from scout.api import create_app
from scout.cli import app
from scout.settings import Settings


def test_schema_export_keeps_catalogue_types_without_enabling_private_serving(tmp_path, monkeypatch):
    monkeypatch.setenv('SCOUT_SERVE_PRIVATE_EVIDENCE', 'false')
    monkeypatch.setenv('SCOUT_DATABASE_URL', f'sqlite:///{tmp_path / "schema.db"}')
    output = tmp_path / 'openapi.json'
    result = CliRunner().invoke(app, ['openapi', '--output', str(output)])
    assert result.exit_code == 0, result.output
    schema = json.loads(output.read_text())
    assert 'PlayerCardData' in schema['components']['schemas']
    assert '/catalogue/players' in schema['paths']
    with TestClient(create_app(Settings(serve_private_evidence=False))) as client:
        assert client.get('/catalogue/players').status_code == 404
