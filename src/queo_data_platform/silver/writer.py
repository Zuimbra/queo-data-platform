from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
from deltalake import DeltaTable, write_deltalake

from queo_data_platform.infrastructure.delta.table import (
    is_delta_table,
)


def dataframe_to_arrow(
    dataframe: pd.DataFrame,
    schema: pa.Schema,
) -> pa.Table:
    """
    Converte um DataFrame Silver usando schema explícito.

    Isso evita NullType e inferências incorretas de tipo,
    especialmente quando o produto Silver está vazio.
    """

    missing_columns = [
        column for column in schema.names if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "O DataFrame Silver não possui todas as colunas "
            f"do contrato: {missing_columns}"
        )

    if dataframe.empty:
        return pa.Table.from_batches(
            [],
            schema=schema,
        )

    aligned = dataframe.reindex(columns=schema.names)

    return pa.Table.from_pandas(
        aligned,
        schema=schema,
        preserve_index=False,
        safe=True,
    )


def validate_partition_column(
    table: pa.Table,
    partition_by: str,
) -> None:
    """
    Confirma que a coluna usada como partição existe
    e permanece textual.
    """

    if partition_by not in table.column_names:
        raise ValueError(f"Coluna de partição ausente: {partition_by}")

    field = table.schema.field(partition_by)

    if not (pa.types.is_string(field.type) or pa.types.is_large_string(field.type)):
        raise ValueError(
            "A coluna de partição Silver precisa ser string: "
            f"{partition_by}={field.type}"
        )


def escape_delta_string_literal(
    value: str,
) -> str:
    """
    Escapa aspas simples para uso em predicates Delta.
    """

    return value.replace(
        "'",
        "''",
    )


def filter_partition(
    table: pa.Table,
    *,
    partition_by: str,
    partition_value: str,
) -> pa.Table:
    """
    Retorna somente uma partição da tabela Arrow.
    """

    column = table[partition_by]

    mask = pc.call_function(
        "equal",
        [
            column,
            pa.scalar(
                partition_value,
                type=column.type,
            ),
        ],
    )

    return table.filter(mask)


def write_full_silver_table(
    table_path: Path,
    table: pa.Table,
    *,
    partition_by: str,
) -> int:
    """
    Executa rebuild completo de um produto Silver.
    """

    validate_partition_column(
        table,
        partition_by,
    )

    table_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    write_deltalake(
        table_path,
        table,
        mode="overwrite",
        schema_mode="overwrite",
        partition_by=[partition_by],
    )

    return table.num_rows


def write_incremental_silver_partitions(
    table_path: Path,
    table: pa.Table,
    *,
    partition_by: str,
    affected_partitions: tuple[str, ...],
) -> int:
    """
    Reconstrói somente as partições informadas.

    Se uma partição afetada não possuir mais registros,
    os registros antigos daquela partição são removidos.
    """

    validate_partition_column(
        table,
        partition_by,
    )

    if not is_delta_table(table_path):
        raise RuntimeError(
            "A escrita incremental Silver exige uma "
            f"Delta Table existente: {table_path}"
        )

    delta_table = DeltaTable(str(table_path))

    rows_written = 0

    for partition_value in affected_partitions:
        partition_table = filter_partition(
            table,
            partition_by=partition_by,
            partition_value=partition_value,
        )

        escaped_value = escape_delta_string_literal(partition_value)

        predicate = f"{partition_by} = '{escaped_value}'"

        if partition_table.num_rows == 0:
            delta_table.delete(predicate)

            continue

        write_deltalake(
            table_path,
            partition_table,
            mode="overwrite",
            predicate=predicate,
        )

        rows_written += partition_table.num_rows

    return rows_written
