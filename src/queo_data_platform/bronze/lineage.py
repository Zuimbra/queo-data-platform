from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pandas as pd

from queo_data_platform.bronze.files import calculate_file_sha256


def generate_batch_id() -> str:
    """
    Gera um identificador único para uma execução de ingestão.

    Cada processamento recebe um novo batch_id, mesmo quando o
    arquivo já foi processado anteriormente.
    """

    return str(uuid4())


def normalize_ingestion_timestamp(
    ingested_at: datetime | None = None,
) -> datetime:
    """
    Normaliza o instante de ingestão para UTC.

    Se nenhum timestamp for informado, utiliza o horário atual.

    Datetimes sem timezone são interpretados como UTC.
    Datetimes com timezone são convertidos para UTC.
    """

    timestamp = ingested_at or datetime.now(UTC)

    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=UTC)

    return timestamp.astimezone(UTC)


def calculate_row_id(
    source_file_hash: str,
    source_row_number: int,
) -> str:
    """
    Gera um identificador determinístico para uma linha da fonte.

    A identidade é formada por:

        hash do arquivo + posição original da linha

    O batch_id não participa do cálculo.

    Portanto, reprocessar exatamente a mesma linha do mesmo
    conteúdo gera sempre o mesmo row_id.
    """

    if not source_file_hash.strip():
        raise ValueError("source_file_hash não pode ser vazio.")

    if source_row_number < 1:
        raise ValueError("source_row_number precisa começar em 1.")

    identity = (
        f"{source_file_hash}:{source_row_number}"
    ).encode()

    return sha256(identity).hexdigest()


def add_lineage_metadata(
    dataframe: pd.DataFrame,
    source_path: Path,
    batch_id: str,
    ingested_at: datetime | None = None,
    source_file_hash: str | None = None,
) -> pd.DataFrame:
    """
    Adiciona os metadados técnicos da Bronze ao DataFrame.

    As colunas originais não são modificadas.

    Metadados adicionados:
    - source_file
    - source_file_hash
    - source_row_number
    - row_id
    - batch_id
    - ingested_at
    - ingestion_date
    """

    if not batch_id.strip():
        raise ValueError("batch_id não pode ser vazio.")

    if not source_path.is_file():
        raise ValueError("source_path precisa representar um arquivo.")

    # Usa o hash fornecido quando ele já foi calculado
    # anteriormente pelo pipeline.
    #
    # Isso evita ler o mesmo arquivo novamente sem necessidade.
    resolved_file_hash = source_file_hash or calculate_file_sha256(source_path)

    ingestion_timestamp = normalize_ingestion_timestamp(ingested_at)

    # Trabalhamos sobre uma cópia para não modificar
    # o DataFrame recebido pelo chamador.
    bronze_dataframe = dataframe.copy()

    # A numeração representa a posição da linha no arquivo
    # original e começa em 1.
    source_row_numbers = list(
        range(
            1,
            len(bronze_dataframe) + 1,
        )
    )

    bronze_dataframe["source_file"] = source_path.name

    bronze_dataframe["source_file_hash"] = resolved_file_hash

    bronze_dataframe["source_row_number"] = source_row_numbers

    bronze_dataframe["row_id"] = [
        calculate_row_id(
            source_file_hash=resolved_file_hash,
            source_row_number=row_number,
        )
        for row_number in source_row_numbers
    ]

    bronze_dataframe["batch_id"] = batch_id

    bronze_dataframe["ingested_at"] = pd.Timestamp(ingestion_timestamp)

    bronze_dataframe["ingestion_date"] = ingestion_timestamp.date().isoformat()

    return bronze_dataframe
