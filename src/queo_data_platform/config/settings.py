import os
from dataclasses import dataclass
from pathlib import Path


def parse_csv_environment_variable(
    name: str,
) -> tuple[str, ...]:
    """
    Converte uma variável de ambiente separada
    por vírgulas em valores normalizados.

    Valores vazios são ignorados e duplicatas
    são removidas preservando a ordem.
    """

    raw_value = os.getenv(
        name,
        "",
    )

    values = [value.strip() for value in raw_value.split(",") if value.strip()]

    return tuple(dict.fromkeys(values))


@dataclass(frozen=True)
class Settings:
    project_root: Path

    data_dir: Path

    raw_dir: Path
    inbox_dir: Path
    archive_dir: Path
    quarantine_dir: Path

    lakehouse_dir: Path
    control_dir: Path
    bronze_dir: Path
    silver_dir: Path
    gold_dir: Path

    api_cors_origins: tuple[str, ...] = ()


def load_settings() -> Settings:
    project_root = Path(__file__).resolve().parents[3]

    data_dir = Path(
        os.getenv(
            "QUEO_DATA_DIR",
            str(project_root / "data"),
        )
    ).resolve()

    raw_dir = data_dir / "raw"

    lakehouse_dir = data_dir / "lakehouse"

    return Settings(
        project_root=project_root,
        data_dir=data_dir,
        raw_dir=raw_dir,
        inbox_dir=(raw_dir / "inbox"),
        archive_dir=(raw_dir / "archive"),
        quarantine_dir=(raw_dir / "quarantine"),
        lakehouse_dir=lakehouse_dir,
        control_dir=(lakehouse_dir / "00_control"),
        bronze_dir=(lakehouse_dir / "01_bronze"),
        silver_dir=(lakehouse_dir / "02_silver"),
        gold_dir=(lakehouse_dir / "03_gold"),
        api_cors_origins=(parse_csv_environment_variable("QUEO_API_CORS_ORIGINS")),
    )


settings = load_settings()
