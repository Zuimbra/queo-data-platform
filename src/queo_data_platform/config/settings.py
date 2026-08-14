import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    """Caminhos utilizados pela plataforma."""

    # Raiz do projeto.
    project_root: Path

    # Diretório principal de dados.
    data_dir: Path

    # Dados de entrada ainda não processados.
    raw_dir: Path

    # Raiz das camadas do Lakehouse.
    lakehouse_dir: Path

    # Tabelas de controle e metadados operacionais.
    control_dir: Path

    # Dados ingeridos com pouca transformação.
    bronze_dir: Path

    # Dados tratados, normalizados e validados.
    silver_dir: Path

    # Dados preparados para consumo.
    gold_dir: Path


def load_settings() -> Settings:
    """Carrega os caminhos utilizados pela aplicação."""

    # settings.py está em:
    # src/queo_data_platform/config/settings.py
    # parents[3] aponta para a raiz do projeto.
    project_root = Path(__file__).resolve().parents[3]

    # Permite sobrescrever o diretório de dados via variável de ambiente.
    # Caso não exista, usa <project_root>/data.
    data_dir = Path(
        os.getenv(
            "QUEO_DATA_DIR",
            str(project_root / "data"),
        )
    ).resolve()

    # Diretórios derivados do diretório principal de dados.
    raw_dir = data_dir / "raw"
    lakehouse_dir = data_dir / "lakehouse"

    return Settings(
        project_root=project_root,
        data_dir=data_dir,
        raw_dir=raw_dir,
        lakehouse_dir=lakehouse_dir,
        control_dir=lakehouse_dir / "00_control",
        bronze_dir=lakehouse_dir / "01_bronze",
        silver_dir=lakehouse_dir / "02_silver",
        gold_dir=lakehouse_dir / "03_gold",
    )


# Instância compartilhada de configuração.
settings = load_settings()
