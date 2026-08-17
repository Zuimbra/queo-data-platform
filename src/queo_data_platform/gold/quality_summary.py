import duckdb
import pandas as pd
import pyarrow as pa

from queo_data_platform.gold.base import (
    SILVER_IDENTITY_RELATION,
    SILVER_REJECTED_RELATION,
    SILVER_TELEMETRY_RELATION,
)


def register_quality_dates(
    connection: duckdb.DuckDBPyConnection,
    metric_dates: tuple[str, ...],
) -> None:
    """
    Registra as datas que precisam ser reconstruídas
    no data_quality_summary.
    """

    connection.register(
        "quality_gold_dates",
        pd.DataFrame({"metric_date": list(metric_dates)}),
    )


def build_data_quality_summary(
    connection: duckdb.DuckDBPyConnection,
    metric_dates: tuple[str, ...] | None = None,
) -> pa.Table:
    """
    Constrói o resumo diário de qualidade da Gold.

    A métrica combina:

    - eventos de telemetria aceitos;
    - eventos de identidade aceitos;
    - registros rejeitados;
    - motivos específicos de rejeição.

    metric_dates=None:
        processa todas as datas.

    metric_dates=(...):
        recalcula somente as datas informadas.
    """

    if metric_dates is not None:
        register_quality_dates(
            connection,
            metric_dates,
        )

        final_filter = """
            WHERE metric_date IN (
                SELECT metric_date
                FROM quality_gold_dates
            )
        """

    else:
        final_filter = ""

    return connection.execute(
        f"""
        WITH telemetry_counts AS (
            SELECT
                CAST(
                    event_date AS VARCHAR
                ) AS metric_date,

                COUNT(*)
                    AS telemetry_event_count

            FROM {SILVER_TELEMETRY_RELATION}

            GROUP BY
                CAST(
                    event_date AS VARCHAR
                )
        ),

        identity_counts AS (
            SELECT
                CAST(
                    event_date AS VARCHAR
                ) AS metric_date,

                COUNT(*)
                    AS identity_event_count

            FROM {SILVER_IDENTITY_RELATION}

            GROUP BY
                CAST(
                    event_date AS VARCHAR
                )
        ),

        rejected_counts AS (
            SELECT
                COALESCE(
                    CAST(
                        rejection_date AS VARCHAR
                    ),
                    'unknown'
                ) AS metric_date,

                COUNT(*)
                    AS rejected_event_count,

                COUNT(*) FILTER (
                    WHERE rejection_reason
                        = 'MISSING_MESSAGE_TYPE'
                ) AS missing_message_type_count,

                COUNT(*) FILTER (
                    WHERE rejection_reason
                        = 'INVALID_MESSAGE_TYPE'
                ) AS invalid_message_type_count,

                COUNT(*) FILTER (
                    WHERE rejection_reason
                        = 'MISSING_OR_INVALID_TIMESTAMP'
                ) AS invalid_timestamp_count,

                COUNT(*) FILTER (
                    WHERE rejection_reason
                        = 'MISSING_DEVICE_SERIAL'
                ) AS missing_device_serial_count,

                COUNT(*) FILTER (
                    WHERE rejection_reason
                        = 'UNKNOWN_REJECTION_REASON'
                ) AS unknown_rejection_count

            FROM {SILVER_REJECTED_RELATION}

            GROUP BY
                COALESCE(
                    CAST(
                        rejection_date AS VARCHAR
                    ),
                    'unknown'
                )
        ),

        all_dates AS (
            SELECT metric_date
            FROM telemetry_counts

            UNION

            SELECT metric_date
            FROM identity_counts

            UNION

            SELECT metric_date
            FROM rejected_counts
        ),

        combined AS (
            SELECT
                all_dates.metric_date,

                COALESCE(
                    telemetry_counts.telemetry_event_count,
                    0
                ) AS telemetry_event_count,

                COALESCE(
                    identity_counts.identity_event_count,
                    0
                ) AS identity_event_count,

                COALESCE(
                    rejected_counts.rejected_event_count,
                    0
                ) AS rejected_event_count,

                COALESCE(
                    rejected_counts.missing_message_type_count,
                    0
                ) AS missing_message_type_count,

                COALESCE(
                    rejected_counts.invalid_message_type_count,
                    0
                ) AS invalid_message_type_count,

                COALESCE(
                    rejected_counts.invalid_timestamp_count,
                    0
                ) AS invalid_timestamp_count,

                COALESCE(
                    rejected_counts.missing_device_serial_count,
                    0
                ) AS missing_device_serial_count,

                COALESCE(
                    rejected_counts.unknown_rejection_count,
                    0
                ) AS unknown_rejection_count

            FROM all_dates

            LEFT JOIN telemetry_counts
                ON all_dates.metric_date
                 = telemetry_counts.metric_date

            LEFT JOIN identity_counts
                ON all_dates.metric_date
                 = identity_counts.metric_date

            LEFT JOIN rejected_counts
                ON all_dates.metric_date
                 = rejected_counts.metric_date
        )

        SELECT
            metric_date,

            telemetry_event_count,
            identity_event_count,

            telemetry_event_count
            + identity_event_count
                AS accepted_event_count,

            rejected_event_count,

            telemetry_event_count
            + identity_event_count
            + rejected_event_count
                AS total_event_count,

            ROUND(
                rejected_event_count
                * 100.0
                / NULLIF(
                    telemetry_event_count
                    + identity_event_count
                    + rejected_event_count,
                    0
                ),
                4
            ) AS rejection_percentage,

            missing_message_type_count,
            invalid_message_type_count,
            invalid_timestamp_count,
            missing_device_serial_count,
            unknown_rejection_count

        FROM combined

        {final_filter}

        ORDER BY metric_date
        """
    ).to_arrow_table()
