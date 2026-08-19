from dataclasses import dataclass

import duckdb
import pandas as pd


@dataclass(frozen=True)
class SilverClassificationResult:
    """
    Resultado da classificação dos registros normalizados.

    Nesta etapa os registros são separados em:
    - candidatos a telemetria;
    - candidatos a identidade;
    - registros rejeitados.
    """

    telemetry: pd.DataFrame
    identity: pd.DataFrame
    rejected: pd.DataFrame


def validate_normalized_input(
    dataframe: pd.DataFrame,
) -> None:
    """
    Confirma que a entrada possui as colunas mínimas necessárias
    para a classificação da Silver.
    """

    required_columns = (
        "server_timestamp",
        "device_timestamp",
        "message_type",
        "device_serial_raw",
        "device_serial",
        "device_resolution_method",
        "row_id",
        "batch_id",
    )

    missing_columns = [
        column for column in required_columns if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "A entrada normalizada não possui todas as colunas "
            f"necessárias para classificação: {missing_columns}"
        )


def classify_normalized_dataframe(
    dataframe: pd.DataFrame,
) -> SilverClassificationResult:
    """
    Classifica registros normalizados da Bronze.

    Regras:

    Telemetria:
        message_type segue T<n>,
        não é T1,
        possui timestamp,
        possui identidade resolvida do dispositivo.

    Identidade:
        message_type é T1,
        possui timestamp,
        possui identidade resolvida do dispositivo.

    Rejeição:
        message_type ausente ou inválido,
        timestamp ausente/inválido,
        identidade resolvida do dispositivo ausente.

    A classificação utiliza device_serial como identidade canônica.
    device_serial_raw é preservado apenas como informação de origem
    para auditoria e rastreabilidade.
    """

    validate_normalized_input(dataframe)

    connection = duckdb.connect()

    try:
        connection.register(
            "normalized_input",
            dataframe,
        )

        connection.execute(
            """
            CREATE OR REPLACE TEMP VIEW classified AS

            SELECT
                normalized_input.*,

                COALESCE(
                    device_timestamp,
                    server_timestamp
                ) AS event_timestamp,

                CASE
                    WHEN message_type IS NULL
                    THEN 'MISSING_MESSAGE_TYPE'

                    WHEN NOT regexp_full_match(
                        message_type,
                        '^T[0-9]+$'
                    )
                    THEN 'INVALID_MESSAGE_TYPE'

                    WHEN COALESCE(
                        device_timestamp,
                        server_timestamp
                    ) IS NULL
                    THEN 'MISSING_OR_INVALID_TIMESTAMP'

                    WHEN device_serial IS NULL
                    THEN 'MISSING_DEVICE_SERIAL'

                    ELSE NULL
                END AS rejection_reason

            FROM normalized_input
            """
        )

        telemetry = connection.execute(
            """
            SELECT
                STRFTIME(
                    event_timestamp,
                    '%Y-%m-%d'
                ) AS event_date,

                * EXCLUDE (rejection_reason)

            FROM classified

            WHERE rejection_reason IS NULL

              AND regexp_full_match(
                    message_type,
                    '^T[0-9]+$'
              )

              AND message_type <> 'T1'
            """
        ).df()

        identity = connection.execute(
            """
            SELECT
                STRFTIME(
                    event_timestamp,
                    '%Y-%m-%d'
                ) AS event_date,

                * EXCLUDE (rejection_reason)

            FROM classified

            WHERE rejection_reason IS NULL
              AND message_type = 'T1'
            """
        ).df()

        rejected = connection.execute(
            """
            SELECT
                COALESCE(
                    STRFTIME(
                        event_timestamp,
                        '%Y-%m-%d'
                    ),
                    'unknown'
                ) AS rejection_date,

                *

            FROM classified

            WHERE rejection_reason IS NOT NULL
            """
        ).df()

        return SilverClassificationResult(
            telemetry=telemetry,
            identity=identity,
            rejected=rejected,
        )

    finally:
        connection.close()
