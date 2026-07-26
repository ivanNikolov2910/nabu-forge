from pathlib import Path

import pytest
from typer.testing import CliRunner

from nabu.cli import app

runner = CliRunner()


@pytest.fixture
def university_schema() -> Path:
    return Path("samples/university/schema.graphqls")


@pytest.fixture
def university_config() -> Path:
    return Path("samples/university/nabu.toml")


def test_version() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0


def test_validate(university_config: Path) -> None:
    result = runner.invoke(app, ["validate", "--config", str(university_config)])

    assert result.exit_code == 0
    assert "OK" in result.output


def test_validate_missing_config(tmp_path: Path) -> None:
    result = runner.invoke(app, ["validate", "--config", str(tmp_path / "nabu.toml")])

    assert result.exit_code == 1


def test_validate_missing_schema(tmp_path: Path) -> None:
    config = tmp_path / "nabu.toml"
    config.write_text(
        'schema = "schema.graphqls"\noperations = "operations/"\noutput = "out"'
    )

    result = runner.invoke(app, ["validate", "--config", str(config)])

    assert result.exit_code == 1


def test_inspect(university_schema: Path) -> None:
    result = runner.invoke(app, ["inspect", "--schema", str(university_schema)])

    assert result.exit_code == 0
    assert "Object types" in result.output
    assert "Queries" in result.output


def test_inspect_missing_schema(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["inspect", "--schema", str(tmp_path / "schema.graphqls")]
    )

    assert result.exit_code == 1


def test_inspect_invalid_schema(tmp_path: Path) -> None:
    schema = tmp_path / "schema.graphqls"
    schema.write_text("type Query { broken: String")

    result = runner.invoke(app, ["inspect", "--schema", str(schema)])

    assert result.exit_code == 1
