from pathlib import Path

from queo_data_platform.config.settings import (
    load_settings,
)


def test_default_data_dir_is_inside_project_root(
    monkeypatch,
) -> None:
    monkeypatch.delenv(
        "QUEO_DATA_DIR",
        raising=False,
    )

    settings = load_settings()

    assert settings.data_dir == (settings.project_root / "data")


def test_directories_are_derived_from_data_dir(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(
        "QUEO_DATA_DIR",
        str(tmp_path),
    )

    settings = load_settings()

    data_dir = tmp_path.resolve()

    assert settings.data_dir == data_dir

    assert settings.raw_dir == (data_dir / "raw")

    assert settings.inbox_dir == (data_dir / "raw" / "inbox")

    assert settings.archive_dir == (data_dir / "raw" / "archive")

    assert settings.quarantine_dir == (data_dir / "raw" / "quarantine")

    assert settings.lakehouse_dir == (data_dir / "lakehouse")

    assert settings.control_dir == (data_dir / "lakehouse" / "00_control")

    assert settings.bronze_dir == (data_dir / "lakehouse" / "01_bronze")

    assert settings.silver_dir == (data_dir / "lakehouse" / "02_silver")

    assert settings.gold_dir == (data_dir / "lakehouse" / "03_gold")
