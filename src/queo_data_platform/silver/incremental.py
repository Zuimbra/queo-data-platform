from dataclasses import dataclass

import duckdb
import pandas as pd
from deltalake import DeltaTable


@dataclass(frozen=True)
class SilverAffectedPartitions:
    """
    Partições Silver afetadas por um conjunto de batches Bronze.
    """

    event_dates: tuple[str, ...]
    rejection_dates: tuple[str, ...]

    @property
    def include_unknown(self) -> bool:
        return "unknown" in self.rejection_dates

    @property
    def is_empty(self) -> bool:
        return not self.event_dates and not self.rejection_dates


def normalize_batch_ids(
    batch_ids: (set[str] | list[str] | tuple[str, ...] | None),
) -> tuple[str, ...]:
    """
    Limpa, remove duplicatas e ordena os batch_ids recebidos.
    """

    if batch_ids is None:
        return ()

    return tuple(
        sorted(
            {str(batch_id).strip() for batch_id in batch_ids if str(batch_id).strip()}
        )
    )


def validate_bronze_incremental_contract(
    bronze_table: DeltaTable,
) -> None:
    """
    Confirma que a Bronze possui os campos necessários
    para descoberta das partições Silver afetadas.
    """

    required_columns = {
        "DATA_SERVIDOR",
        "TM_STAMP",
        "batch_id",
    }

    available_columns = {field.name for field in bronze_table.schema().fields}

    missing_columns = sorted(required_columns - available_columns)

    if missing_columns:
        raise ValueError(
            "A Bronze não possui todas as colunas "
            "necessárias para incrementalidade Silver: "
            f"{missing_columns}"
        )


def discover_affected_partitions(
    bronze_table: DeltaTable,
    batch_ids: (set[str] | list[str] | tuple[str, ...] | None),
) -> SilverAffectedPartitions:
    """
    Descobre as partições Silver impactadas pelos batches.

    Para timestamps válidos:
        event_date = YYYY-MM-DD

    Para registros sem nenhum timestamp válido:
        rejection_date = unknown
    """

    normalized_batch_ids = normalize_batch_ids(batch_ids)

    if not normalized_batch_ids:
        return SilverAffectedPartitions(
            event_dates=(),
            rejection_dates=(),
        )

    validate_bronze_incremental_contract(bronze_table)

    connection = duckdb.connect()

    try:
        connection.register(
            "bronze",
            bronze_table.to_pyarrow_dataset(),
        )

        requested_batches = pd.DataFrame(
            {
                "batch_id": pd.Series(
                    normalized_batch_ids,
                    dtype="string",
                )
            }
        )

        connection.register(
            "requested_silver_batches",
            requested_batches,
        )

        affected_dates = connection.execute(
            """
            WITH requested_rows AS (
                SELECT
                    COALESCE(
                        TRY_CAST(
                            bronze."TM_STAMP"
                            AS TIMESTAMP
                        ),
                        TRY_CAST(
                            bronze."DATA_SERVIDOR"
                            AS TIMESTAMP
                        )
                    ) AS event_timestamp

                FROM bronze

                INNER JOIN requested_silver_batches
                    ON CAST(
                        bronze.batch_id AS VARCHAR
                    ) = requested_silver_batches.batch_id
            )

            SELECT DISTINCT
                STRFTIME(
                    event_timestamp,
                    '%Y-%m-%d'
                ) AS event_date

            FROM requested_rows

            WHERE event_timestamp IS NOT NULL

            ORDER BY event_date
            """
        ).df()

        unknown_result = connection.execute(
            """
            SELECT EXISTS (
                SELECT 1

                FROM bronze

                INNER JOIN requested_silver_batches
                    ON CAST(
                        bronze.batch_id AS VARCHAR
                    ) = requested_silver_batches.batch_id

                WHERE COALESCE(
                    TRY_CAST(
                        bronze."TM_STAMP"
                        AS TIMESTAMP
                    ),
                    TRY_CAST(
                        bronze."DATA_SERVIDOR"
                        AS TIMESTAMP
                    )
                ) IS NULL
            )
            """
        ).fetchone()

        has_unknown = bool(unknown_result and unknown_result[0])

        event_dates = tuple(affected_dates["event_date"].dropna().astype(str).tolist())

        rejection_dates = event_dates

        if has_unknown:
            rejection_dates = (
                *rejection_dates,
                "unknown",
            )

        return SilverAffectedPartitions(
            event_dates=event_dates,
            rejection_dates=(rejection_dates),
        )

    finally:
        connection.close()


def load_incremental_bronze_scope(
    bronze_table: DeltaTable,
    affected_partitions: SilverAffectedPartitions,
) -> pd.DataFrame:
    """
    Carrega todas as linhas Bronze pertencentes às partições
    afetadas.

    Importante:
    o filtro não utiliza batch_id.

    Os batches servem apenas para descobrir as datas afetadas.
    Depois disso toda a partição precisa ser reconstruída.
    """

    validate_bronze_incremental_contract(bronze_table)

    connection = duckdb.connect()

    try:
        connection.register(
            "bronze",
            bronze_table.to_pyarrow_dataset(),
        )

        if affected_partitions.is_empty:
            return connection.execute(
                """
                SELECT *
                FROM bronze
                WHERE FALSE
                """
            ).df()

        affected_dates = pd.DataFrame(
            {
                "event_date": pd.Series(
                    affected_partitions.event_dates,
                    dtype="string",
                )
            }
        )

        connection.register(
            "affected_silver_dates",
            affected_dates,
        )

        include_unknown = "TRUE" if affected_partitions.include_unknown else "FALSE"

        return connection.execute(
            f"""
            WITH scoped AS (
                SELECT
                    bronze.*,

                    COALESCE(
                        TRY_CAST(
                            bronze."TM_STAMP"
                            AS TIMESTAMP
                        ),
                        TRY_CAST(
                            bronze."DATA_SERVIDOR"
                            AS TIMESTAMP
                        )
                    ) AS _scope_event_timestamp

                FROM bronze
            )

            SELECT
                scoped.*
                    EXCLUDE (
                        _scope_event_timestamp
                    )

            FROM scoped

            LEFT JOIN affected_silver_dates
                ON STRFTIME(
                    scoped._scope_event_timestamp,
                    '%Y-%m-%d'
                ) = affected_silver_dates.event_date

            WHERE
                affected_silver_dates.event_date
                    IS NOT NULL

                OR (
                    {include_unknown}
                    AND scoped._scope_event_timestamp
                        IS NULL
                )
            """
        ).df()

    finally:
        connection.close()
