from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
from deltalake import DeltaTable, write_deltalake

from queo_data_platform.infrastructure.delta.table import (
    is_delta_table,
)


def align_gold_table(
    table: pa.Table,
    schema: pa.Schema,
) -> pa.Table:
    """
    Alinha uma Arrow Table produzida pela Gold ao
    schema oficial do produto.

    O schema do contrato é a fonte de verdade.

    Para resultados vazios, uma nova Arrow Table vazia
    é criada diretamente com o schema explícito.
    """

    missing_columns = [
        column for column in schema.names if column not in table.column_names
    ]

    if missing_columns:
        raise ValueError(
            f"O produto Gold não possui todas as colunas do contrato: {missing_columns}"
        )

    if table.num_rows == 0:
        return pa.Table.from_batches(
            [],
            schema=schema,
        )

    ordered = table.select(schema.names)

    return ordered.cast(
        schema,
        safe=True,
    )


def validate_partition_column(
    table: pa.Table,
    partition_by: str,
) -> None:
    """
    Confirma que a coluna de partição existe
    e possui tipo string.
    """

    if partition_by not in table.column_names:
        raise ValueError(f"Coluna de partição Gold ausente: {partition_by}")

    field = table.schema.field(partition_by)

    if not (pa.types.is_string(field.type) or pa.types.is_large_string(field.type)):
        raise ValueError(
            f"A coluna de partição Gold precisa ser string: {partition_by}={field.type}"
        )


def validate_entity_key(
    table: pa.Table,
    key_column: str,
) -> None:
    """
    Valida a chave usada pelo MERGE das tabelas
    de entidade Gold.
    """

    if key_column not in table.column_names:
        raise ValueError(f"Chave de entidade Gold ausente: {key_column}")

    if table.num_rows == 0:
        return

    key_values = table[key_column].to_pylist()

    if any(value is None for value in key_values):
        raise ValueError(f"A chave de entidade Gold não pode conter NULL: {key_column}")

    if len(key_values) != len(set(key_values)):
        raise ValueError(
            f"A origem do MERGE Gold possui chaves duplicadas: {key_column}"
        )


def escape_delta_string_literal(
    value: str,
) -> str:
    """
    Escapa aspas simples usadas em predicates Delta.
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
    Retorna somente os registros pertencentes
    à partição informada.
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


def write_gold_entity_table(
    table_path: Path,
    table: pa.Table,
    *,
    schema: pa.Schema,
    key_column: str,
    full_rebuild: bool,
) -> int:
    """
    Persiste uma tabela Gold baseada em entidade.

    FULL:
        substitui completamente a tabela.

    INCREMENTAL:
        realiza MERGE pela chave da entidade.
    """

    aligned = align_gold_table(
        table,
        schema,
    )

    validate_entity_key(
        aligned,
        key_column,
    )

    table_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if full_rebuild:
        write_deltalake(
            table_path,
            aligned,
            mode="overwrite",
            schema_mode="overwrite",
        )

        return aligned.num_rows

    if not is_delta_table(table_path):
        raise RuntimeError(
            f"O MERGE incremental Gold exige uma Delta Table existente: {table_path}"
        )

    if aligned.num_rows == 0:
        return 0

    delta_table = DeltaTable(str(table_path))

    (
        delta_table.merge(
            source=aligned,
            predicate=(f"target.{key_column} = source.{key_column}"),
            source_alias="source",
            target_alias="target",
        )
        .when_matched_update_all()
        .when_not_matched_insert_all()
        .execute()
    )

    return aligned.num_rows


def write_gold_partitioned_table(
    table_path: Path,
    table: pa.Table,
    *,
    schema: pa.Schema,
    partition_by: str,
    full_rebuild: bool,
    affected_partitions: tuple[str, ...] = (),
) -> int:
    """
    Persiste produtos Gold particionados.

    FULL:
        substitui completamente a tabela.

    INCREMENTAL:
        reconstrói somente as partições afetadas.

    Se uma partição afetada não possuir mais registros,
    os dados antigos daquela partição são removidos.
    """

    aligned = align_gold_table(
        table,
        schema,
    )

    validate_partition_column(
        aligned,
        partition_by,
    )

    table_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if full_rebuild:
        write_deltalake(
            table_path,
            aligned,
            mode="overwrite",
            schema_mode="overwrite",
            partition_by=[partition_by],
        )

        return aligned.num_rows

    if not is_delta_table(table_path):
        raise RuntimeError(
            f"O replace incremental Gold exige uma Delta Table existente: {table_path}"
        )

    if not affected_partitions:
        return 0

    delta_table = DeltaTable(str(table_path))

    rows_written = 0

    for partition_value in affected_partitions:
        partition_table = filter_partition(
            aligned,
            partition_by=partition_by,
            partition_value=(partition_value),
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
