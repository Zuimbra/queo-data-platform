from pathlib import Path

from queo_data_platform.config.settings import load_settings


def test_default_data_dir_is_inside_project_root(
    monkeypatch,
) -> None:
    # Garante que o teste representa o comportamento padrão,
    # sem QUEO_DATA_DIR configurado externamente.
    monkeypatch.delenv("QUEO_DATA_DIR", raising=False)

    settings = load_settings()

    assert settings.data_dir == settings.project_root / "data"


def test_lakehouse_directories_are_derived_from_data_dir(
    monkeypatch,
    tmp_path: Path,
) -> None:
    # Simula um diretório externo como aconteceria em servidor,
    # Docker ou outro ambiente.
    monkeypatch.setenv("QUEO_DATA_DIR", str(tmp_path))

    settings = load_settings()

    assert settings.data_dir == tmp_path.resolve()

    assert settings.raw_dir == tmp_path.resolve() / "raw"

    assert settings.lakehouse_dir == (tmp_path.resolve() / "lakehouse")

    assert settings.control_dir == (tmp_path.resolve() / "lakehouse" / "00_control")

    assert settings.bronze_dir == (tmp_path.resolve() / "lakehouse" / "01_bronze")

    assert settings.silver_dir == (tmp_path.resolve() / "lakehouse" / "02_silver")

    assert settings.gold_dir == (tmp_path.resolve() / "lakehouse" / "03_gold")
