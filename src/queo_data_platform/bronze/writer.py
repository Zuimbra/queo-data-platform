from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import pyarrow as pa
from deltalake import write_deltalake

from queo_data_platform.infrastructure.delta.table import (
    is_delta_table,
    open_delta_table,
)

BRONZE_PARTITION_COLUMN = "ingestion_date"


@dataclass(frozen=True)
class BronzeWriteResult:
    """
    Resume o resultado de uma escrita na tabela Bronze.
    """

    table_path: Path

    # Quantidade de linhas recebidas para escrita.
    row_count: int

    # Quantidade efetivamente inserida na Delta Table.
    inserted_row_count: int

    # Quantidade ignorada porque o row_id já existia.
    duplicate_row_count: int

    # CREATE para primeira escrita ou MERGE para incrementais.
    operation: Literal["CREATE", "MERGE"]

    # Métricas retornadas pelo Delta Lake.
    metrics: dict[str, Any]


def align_dataframe_to_target_schema(
    dataframe: pd.DataFrame,
    target_columns: list[str],
) -> pd.DataFrame:
    """
    Alinha um novo DataFrame ao schema já existente na tabela.

    Colunas existentes no target, mas ausentes na nova fonte,
    recebem NULL.

    Colunas novas são preservadas para que o Delta possa
    evoluir o schema durante o MERGE.
    """

    aligned = dataframe.copy()

    # Completa colunas que já existem na tabela,
    # mas não chegaram neste arquivo.
    for column in target_columns:
        if column not in aligned.columns:
            aligned[column] = None

    # Descobre eventuais colunas novas da fonte.
    new_columns = [column for column in aligned.columns if column not in target_columns]

    # Primeiro mantemos a ordem conhecida do target.
    # Depois colocamos eventuais colunas novas.
    return aligned[
        [
            *target_columns,
            *new_columns,
        ]
    ]


def validate_bronze_dataframe(
    dataframe: pd.DataFrame,
) -> None:
    """
    Valida os requisitos mínimos necessários para persistência.

    Neste ponto o arquivo já passou pela validação estrutural
    da Bronze e pelo enriquecimento de lineage.
    """

    if dataframe.empty:
        raise ValueError("Não é possível escrever um DataFrame vazio na Bronze.")

    required_columns = (
        "row_id",
        BRONZE_PARTITION_COLUMN,
    )

    missing_columns = [
        column for column in required_columns if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "O DataFrame Bronze não possui as colunas "
            f"necessárias para escrita: {missing_columns}"
        )


def dataframe_to_arrow(
    dataframe: pd.DataFrame,
) -> pa.Table:
    """
    Converte um DataFrame Pandas para uma tabela Arrow.

    O índice do Pandas não faz parte do dado armazenado.
    """

    return pa.Table.from_pandas(
        dataframe,
        preserve_index=False,
    )


def write_bronze_table(
    dataframe: pd.DataFrame,
    table_path: Path,
) -> BronzeWriteResult:
    """
    Persiste registros na Bronze consolidada.

    Primeira escrita:
        cria uma Delta Table particionada por ingestion_date.

    Escritas seguintes:
        executam MERGE insert-only usando row_id.

    Isso torna a escrita idempotente: uma mesma linha da mesma
    origem pode ser reenviada sem gerar uma nova linha na Bronze.
    """

    validate_bronze_dataframe(dataframe)

    # Garante que o diretório pai da tabela exista.
    table_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # PRIMEIRA ESCRITA
    # --------------------------------------------------------

    if not is_delta_table(table_path):
        source_table = dataframe_to_arrow(dataframe)

        write_deltalake(
            table_path,
            source_table,
            mode="overwrite",
            partition_by=[BRONZE_PARTITION_COLUMN],
        )

        return BronzeWriteResult(
            table_path=table_path,
            row_count=len(dataframe),
            inserted_row_count=len(dataframe),
            duplicate_row_count=0,
            operation="CREATE",
            metrics={
                "num_source_rows": len(dataframe),
                "num_target_rows_inserted": len(dataframe),
            },
        )

    # --------------------------------------------------------
    # ESCRITA INCREMENTAL
    # --------------------------------------------------------

    bronze_table = open_delta_table(table_path)

    # Obtém as colunas já existentes no target.
    target_columns = [field.name for field in bronze_table.schema().fields]

    aligned_dataframe = align_dataframe_to_target_schema(
        dataframe=dataframe,
        target_columns=target_columns,
    )

    source_table = dataframe_to_arrow(aligned_dataframe)

    # MERGE insert-only:
    #
    # row_id já existe
    #     → não faz nada
    #
    # row_id não existe
    #     → insere
    metrics = (
        bronze_table.merge(
            source=source_table,
            predicate="target.row_id = source.row_id",
            source_alias="source",
            target_alias="target",
            merge_schema=True,
        )
        .when_not_matched_insert_all()
        .execute()
    )

    inserted_row_count = int(
        metrics.get(
            "num_target_rows_inserted",
            0,
        )
    )

    duplicate_row_count = len(dataframe) - inserted_row_count

    return BronzeWriteResult(
        table_path=table_path,
        row_count=len(dataframe),
        inserted_row_count=inserted_row_count,
        duplicate_row_count=duplicate_row_count,
        operation="MERGE",
        metrics=dict(metrics),
    )
