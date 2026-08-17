import duckdb
import pandas as pd

from queo_data_platform.contracts.tracker import (
    BRONZE_REQUIRED_COLUMNS,
)

TEXT_COLUMN_MAPPING = {
    "TIPO_LOG": "log_type",
    "MESS_TYPE": "message_type",
    "REPT_TYPE": "report_type_raw",
    "PRT_VER": "protocol_version",
    "S/N ou IMEI": "device_serial_raw",
    "TERM_STATUS": "terminal_status",
    "BAT_VOLT": "battery_voltage_raw",
    "LOC_STATUS": "location_status_raw",
    "LAT": "latitude_raw",
    "LONT": "longitude_raw",
    "SPEED": "speed_raw",
    "DIR": "direction_raw",
    "INT_BATT": "internal_battery_raw",
    "ODO_TRIP": "odometer_trip_raw",
    "ODO_TOTAL": "odometer_total_raw",
    "HORIMETER": "horimeter_raw",
    "HDOP": "hdop_raw",
    "MCC": "mcc",
    "MNC": "mnc",
    "LAC": "lac",
    "CELL_ID": "cell_id",
    "RX_LEVEL": "rx_level_raw",
    "SER_COUNT": "serial_count_raw",
    "TX_TECH": "transmission_technology",
    "GRP_MSG": "message_group",
    "IO_STATUS": "io_status",
    "DRIVER_ID": "driver_id",
    "PASS_ID": "passenger_id",
    "RPM": "rpm_raw",
    "TACHO_SPD": "tachograph_speed_raw",
    "TACHO_ODO": "tachograph_odometer_raw",
    "TEMP_1": "temperature_1_raw",
    "TEMP_2": "temperature_2_raw",
    "TEMP_3": "temperature_3_raw",
    "TEMP_4": "temperature_4_raw",
}


def validate_bronze_input_columns(
    dataframe: pd.DataFrame,
) -> None:
    """
    Confirma que a entrada possui o contrato mínimo esperado
    pela Silver.
    """

    available_columns = set(dataframe.columns)

    missing_columns = [
        column for column in BRONZE_REQUIRED_COLUMNS if column not in available_columns
    ]

    if missing_columns:
        raise ValueError(
            "A entrada Bronze não possui todas as colunas "
            f"necessárias para a Silver: {missing_columns}"
        )


def build_text_normalization_expression(
    source_column: str,
    target_column: str,
) -> str:
    """
    Gera a expressão SQL usada para normalizar campos textuais.

    Espaços externos são removidos e strings vazias
    são convertidas para NULL.
    """

    return (
        f'NULLIF(TRIM(CAST("{source_column}" AS VARCHAR)), \'\') AS "{target_column}"'
    )


def build_normalization_query(
    source_relation: str,
) -> str:
    """
    Monta a projeção comum Bronze -> Silver.

    A classificação entre telemetria, identidade e rejeição
    ainda não acontece aqui.
    """

    text_expressions = [
        build_text_normalization_expression(
            source_column,
            target_column,
        )
        for source_column, target_column in TEXT_COLUMN_MAPPING.items()
    ]

    normalized_text_sql = ",\n        ".join(text_expressions)

    return f"""
        SELECT
            TRY_CAST(
                "DATA_SERVIDOR" AS TIMESTAMP
            ) AS server_timestamp,

            TRY_CAST(
                "TM_STAMP" AS TIMESTAMP
            ) AS device_timestamp,

            {normalized_text_sql},

            CAST(source_file AS VARCHAR)
                AS source_file,

            CAST(source_file_hash AS VARCHAR)
                AS source_file_hash,

            CAST(source_row_number AS BIGINT)
                AS source_row_number,

            CAST(row_id AS VARCHAR)
                AS row_id,

            CAST(batch_id AS VARCHAR)
                AS batch_id,

            CAST(ingested_at AS TIMESTAMP)
                AS ingested_at,

            CAST(ingestion_date AS DATE)
                AS ingestion_date

        FROM {source_relation}
    """


def normalize_bronze_dataframe(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Normaliza registros Bronze para a representação comum
    utilizada pelas transformações Silver.

    Essa função ainda não decide se uma linha representa:
    - telemetria;
    - identidade;
    - rejeição.
    """

    validate_bronze_input_columns(dataframe)

    connection = duckdb.connect()

    try:
        connection.register(
            "bronze_input",
            dataframe,
        )

        query = build_normalization_query("bronze_input")

        return connection.execute(query).df()

    finally:
        connection.close()
