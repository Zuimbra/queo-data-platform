import duckdb

SILVER_TELEMETRY_RELATION = "silver_telemetry"

SILVER_IDENTITY_RELATION = "silver_identity"

SILVER_REJECTED_RELATION = "silver_rejected"


TELEMETRY_GOLD_BASE_VIEW = "telemetry_gold_base"

IDENTITY_GOLD_BASE_VIEW = "identity_gold_base"


def create_gold_base_views(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    """
    Cria as views intermediárias utilizadas pelos
    produtos Gold.

    As fontes Silver precisam estar previamente
    registradas na conexão DuckDB como:

    - silver_telemetry
    - silver_identity
    - silver_rejected

    rejected_logs não possui uma base deduplicada aqui,
    pois será utilizado diretamente pelo produto
    data_quality_summary.
    """

    connection.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW
            {TELEMETRY_GOLD_BASE_VIEW}
        AS

        SELECT *

        FROM {SILVER_TELEMETRY_RELATION}

        WHERE device_serial IS NOT NULL
          AND event_timestamp IS NOT NULL

        QUALIFY
            ROW_NUMBER() OVER (
                PARTITION BY
                    device_serial,
                    event_timestamp,
                    message_type,

                    COALESCE(
                        CAST(
                            serial_count
                            AS VARCHAR
                        ),
                        '__NULL__'
                    ),

                    COALESCE(
                        CAST(
                            latitude
                            AS VARCHAR
                        ),
                        '__NULL__'
                    ),

                    COALESCE(
                        CAST(
                            longitude
                            AS VARCHAR
                        ),
                        '__NULL__'
                    ),

                    COALESCE(
                        CAST(
                            speed
                            AS VARCHAR
                        ),
                        '__NULL__'
                    )

                ORDER BY
                    server_timestamp
                        DESC NULLS LAST,

                    source_file
                        DESC NULLS LAST
            ) = 1
        """
    )

    connection.execute(
        f"""
        CREATE OR REPLACE TEMP VIEW
            {IDENTITY_GOLD_BASE_VIEW}
        AS

        SELECT *

        FROM {SILVER_IDENTITY_RELATION}

        WHERE device_serial IS NOT NULL
          AND event_timestamp IS NOT NULL

        QUALIFY
            ROW_NUMBER() OVER (
                PARTITION BY
                    device_serial,
                    event_timestamp,

                    COALESCE(
                        imei,
                        '__NULL__'
                    ),

                    COALESCE(
                        imsi,
                        '__NULL__'
                    ),

                    COALESCE(
                        iccid,
                        '__NULL__'
                    )

                ORDER BY
                    server_timestamp
                        DESC NULLS LAST,

                    source_file
                        DESC NULLS LAST
            ) = 1
        """
    )
