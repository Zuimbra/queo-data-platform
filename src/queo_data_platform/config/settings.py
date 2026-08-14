import os
from dataclasses import dataclass
from pathlib import Path


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
        inbox_dir=raw_dir / "inbox",
        archive_dir=raw_dir / "archive",
        quarantine_dir=raw_dir / "quarantine",
        lakehouse_dir=lakehouse_dir,
        control_dir=lakehouse_dir / "00_control",
        bronze_dir=lakehouse_dir / "01_bronze",
        silver_dir=lakehouse_dir / "02_silver",
        gold_dir=lakehouse_dir / "03_gold",
    )


settings = load_settings()
