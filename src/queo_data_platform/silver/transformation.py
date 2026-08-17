import duckdb
import pandas as pd


def validate_telemetry_input(
    dataframe: pd.DataFrame,
) -> None:
    required_columns = (
        "server_timestamp",
        "device_timestamp",
        "event_timestamp",
        "event_date",
        "message_type",
        "report_type_raw",
        "protocol_version",
        "device_serial_raw",
        "battery_voltage_raw",
        "location_status_raw",
        "latitude_raw",
        "longitude_raw",
        "speed_raw",
        "direction_raw",
        "internal_battery_raw",
        "odometer_trip_raw",
        "odometer_total_raw",
        "horimeter_raw",
        "hdop_raw",
        "rx_level_raw",
        "serial_count_raw",
        "rpm_raw",
        "tachograph_speed_raw",
        "tachograph_odometer_raw",
        "temperature_1_raw",
        "temperature_2_raw",
        "temperature_3_raw",
        "temperature_4_raw",
        "row_id",
        "batch_id",
    )

    missing_columns = [
        column for column in required_columns if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "A entrada de telemetria não possui todas as colunas "
            f"necessárias: {missing_columns}"
        )


def validate_identity_input(
    dataframe: pd.DataFrame,
) -> None:
    required_columns = (
        "server_timestamp",
        "device_timestamp",
        "event_timestamp",
        "event_date",
        "message_type",
        "report_type_raw",
        "protocol_version",
        "device_serial_raw",
        "battery_voltage_raw",
        "location_status_raw",
        "latitude_raw",
        "longitude_raw",
        "row_id",
        "batch_id",
    )

    missing_columns = [
        column for column in required_columns if column not in dataframe.columns
    ]

    if missing_columns:
        raise ValueError(
            "A entrada de identidade não possui todas as colunas "
            f"necessárias: {missing_columns}"
        )


def transform_telemetry_dataframe(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Converte candidatos de telemetria no produto Silver tipado.

    Conversões inválidas resultam em NULL, preservando o registro.
    """

    validate_telemetry_input(dataframe)

    connection = duckdb.connect()

    try:
        connection.register(
            "telemetry_input",
            dataframe,
        )

        return connection.execute(
            """
            WITH typed AS (
                SELECT
                    event_date,
                    server_timestamp,
                    device_timestamp,
                    event_timestamp,

                    log_type,
                    message_type,

                    TRY_CAST(
                        TRY_CAST(
                            report_type_raw AS DOUBLE
                        ) AS INTEGER
                    ) AS report_type,

                    protocol_version,

                    REGEXP_REPLACE(
                        device_serial_raw,
                        '^M',
                        ''
                    ) AS device_serial,

                    terminal_status,

                    TRY_CAST(
                        battery_voltage_raw AS DOUBLE
                    ) AS battery_voltage,

                    location_status_raw
                        AS location_status,

                    TRY_CAST(
                        latitude_raw AS DOUBLE
                    ) AS latitude,

                    TRY_CAST(
                        longitude_raw AS DOUBLE
                    ) AS longitude,

                    TRY_CAST(
                        speed_raw AS DOUBLE
                    ) AS speed,

                    TRY_CAST(
                        direction_raw AS DOUBLE
                    ) AS direction_degrees,

                    TRY_CAST(
                        internal_battery_raw AS DOUBLE
                    ) AS internal_battery,

                    TRY_CAST(
                        odometer_trip_raw AS DOUBLE
                    ) AS odometer_trip,

                    TRY_CAST(
                        odometer_total_raw AS DOUBLE
                    ) AS odometer_total,

                    TRY_CAST(
                        horimeter_raw AS DOUBLE
                    ) AS horimeter,

                    TRY_CAST(
                        hdop_raw AS DOUBLE
                    ) AS hdop,

                    mcc,
                    mnc,
                    lac,
                    cell_id,

                    TRY_CAST(
                        rx_level_raw AS DOUBLE
                    ) AS rx_level,

                    TRY_CAST(
                        TRY_CAST(
                            serial_count_raw AS DOUBLE
                        ) AS BIGINT
                    ) AS serial_count,

                    transmission_technology,
                    message_group,
                    io_status,
                    driver_id,
                    passenger_id,

                    TRY_CAST(
                        rpm_raw AS DOUBLE
                    ) AS rpm,

                    TRY_CAST(
                        tachograph_speed_raw AS DOUBLE
                    ) AS tachograph_speed,

                    TRY_CAST(
                        tachograph_odometer_raw AS DOUBLE
                    ) AS tachograph_odometer,

                    TRY_CAST(
                        temperature_1_raw AS DOUBLE
                    ) AS temperature_1,

                    TRY_CAST(
                        temperature_2_raw AS DOUBLE
                    ) AS temperature_2,

                    TRY_CAST(
                        temperature_3_raw AS DOUBLE
                    ) AS temperature_3,

                    TRY_CAST(
                        temperature_4_raw AS DOUBLE
                    ) AS temperature_4,

                    source_file,
                    source_file_hash,
                    source_row_number,
                    row_id,
                    batch_id,
                    ingested_at,
                    ingestion_date

                FROM telemetry_input
            )

            SELECT
                typed.*,

                CASE
                    WHEN latitude IS NULL
                      OR longitude IS NULL
                    THEN FALSE

                    WHEN latitude NOT BETWEEN -90 AND 90
                      OR longitude NOT BETWEEN -180 AND 180
                    THEN FALSE

                    ELSE TRUE
                END AS has_valid_coordinates,

                CASE
                    WHEN latitude IS NULL
                      OR longitude IS NULL
                    THEN 'MISSING_COORDINATES'

                    WHEN latitude NOT BETWEEN -90 AND 90
                      OR longitude NOT BETWEEN -180 AND 180
                    THEN 'INVALID_COORDINATES'

                    WHEN hdop IS NOT NULL
                     AND hdop > 5
                    THEN 'LOW_GPS_PRECISION'

                    ELSE 'VALID'
                END AS position_quality

            FROM typed
            """
        ).df()

    finally:
        connection.close()


def transform_identity_dataframe(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """
    Converte mensagens T1 no produto Silver de identidade.
    """

    validate_identity_input(dataframe)

    connection = duckdb.connect()

    try:
        connection.register(
            "identity_input",
            dataframe,
        )

        return connection.execute(
            """
            WITH typed AS (
                SELECT
                    event_date,
                    server_timestamp,
                    device_timestamp,
                    event_timestamp,

                    message_type,

                    TRY_CAST(
                        TRY_CAST(
                            report_type_raw AS DOUBLE
                        ) AS INTEGER
                    ) AS report_type,

                    protocol_version,

                    device_serial_raw,

                    REGEXP_REPLACE(
                        device_serial_raw,
                        '^M',
                        ''
                    ) AS device_serial,

                    battery_voltage_raw
                        AS iccid,

                    location_status_raw
                        AS identity_auxiliary,

                    latitude_raw
                        AS imsi,

                    longitude_raw
                        AS imei,

                    source_file,
                    source_file_hash,
                    source_row_number,
                    row_id,
                    batch_id,
                    ingested_at,
                    ingestion_date

                FROM identity_input
            )

            SELECT
                typed.*,

                CASE
                    WHEN iccid IS NULL
                    THEN FALSE

                    WHEN regexp_full_match(
                        iccid,
                        '^[0-9]{18,22}$'
                    )
                    THEN TRUE

                    ELSE FALSE
                END AS has_valid_iccid_format,

                CASE
                    WHEN imsi IS NULL
                    THEN FALSE

                    WHEN regexp_full_match(
                        imsi,
                        '^[0-9]{14,16}$'
                    )
                    THEN TRUE

                    ELSE FALSE
                END AS has_valid_imsi_format,

                CASE
                    WHEN imei IS NULL
                    THEN FALSE

                    WHEN regexp_full_match(
                        imei,
                        '^[0-9]{15}$'
                    )
                    THEN TRUE

                    ELSE FALSE
                END AS has_valid_imei_format

            FROM typed
            """
        ).df()

    finally:
        connection.close()
