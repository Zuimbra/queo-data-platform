import duckdb
import pandas as pd
import pyarrow as pa

from queo_data_platform.gold.base import (
    TELEMETRY_GOLD_BASE_VIEW,
)


def register_daily_summary_dates(
    connection: duckdb.DuckDBPyConnection,
    event_dates: tuple[str, ...],
) -> None:
    """
    Registra as datas que precisam ser reconstruídas
    no device_daily_summary.
    """

    connection.register(
        "daily_gold_dates",
        pd.DataFrame({"event_date": list(event_dates)}),
    )


def build_device_daily_summary(
    connection: duckdb.DuckDBPyConnection,
    event_dates: tuple[str, ...] | None = None,
) -> pa.Table:
    """
    Constrói o resumo diário de telemetria por dispositivo.

    event_dates=None:
        processa todo o histórico disponível.

    event_dates=(...):
        recalcula somente as datas informadas.
    """

    if event_dates is not None:
        register_daily_summary_dates(
            connection,
            event_dates,
        )

        date_filter = """
            WHERE STRFTIME(
                event_timestamp,
                '%Y-%m-%d'
            ) IN (
                SELECT event_date
                FROM daily_gold_dates
            )
        """

    else:
        date_filter = ""

    return connection.execute(
        f"""
        WITH daily_aggregated AS (
            SELECT
                STRFTIME(
                    event_timestamp,
                    '%Y-%m-%d'
                ) AS event_date,

                device_serial,

                MIN(event_timestamp)
                    AS first_event_at,

                MAX(event_timestamp)
                    AS last_event_at,

                COUNT(*)
                    AS message_count,

                COUNT(
                    DISTINCT message_type
                ) AS distinct_message_type_count,

                COUNT(*) FILTER (
                    WHERE has_valid_coordinates = TRUE
                ) AS valid_position_count,

                COUNT(*) FILTER (
                    WHERE has_valid_coordinates IS NOT TRUE
                ) AS invalid_position_count,

                COUNT(*) FILTER (
                    WHERE position_quality
                        = 'LOW_GPS_PRECISION'
                ) AS low_gps_precision_count,

                COUNT(*) FILTER (
                    WHERE speed >= 5
                ) AS moving_event_count,

                COUNT(*) FILTER (
                    WHERE speed IS NOT NULL
                      AND speed < 5
                ) AS stopped_event_count,

                ROUND(
                    AVG(speed),
                    3
                ) AS average_speed,

                ROUND(
                    AVG(speed) FILTER (
                        WHERE speed >= 5
                    ),
                    3
                ) AS average_speed_while_moving,

                MAX(speed)
                    AS maximum_speed,

                ROUND(
                    AVG(hdop),
                    3
                ) AS average_hdop,

                MIN(hdop)
                    AS minimum_hdop,

                MAX(hdop)
                    AS maximum_hdop,

                MIN(battery_voltage)
                    AS minimum_battery_voltage,

                MAX(battery_voltage)
                    AS maximum_battery_voltage,

                ROUND(
                    AVG(battery_voltage),
                    3
                ) AS average_battery_voltage,

                MIN(internal_battery)
                    AS minimum_internal_battery,

                MAX(internal_battery)
                    AS maximum_internal_battery,

                ROUND(
                    AVG(internal_battery),
                    3
                ) AS average_internal_battery,

                ARG_MIN(
                    odometer_total,
                    event_timestamp
                ) AS first_odometer_total,

                ARG_MAX(
                    odometer_total,
                    event_timestamp
                ) AS last_odometer_total,

                MIN(event_timestamp) FILTER (
                    WHERE has_valid_coordinates = TRUE
                ) AS first_valid_position_at,

                MAX(event_timestamp) FILTER (
                    WHERE has_valid_coordinates = TRUE
                ) AS last_valid_position_at,

                ARG_MIN(
                    latitude,
                    event_timestamp
                ) FILTER (
                    WHERE has_valid_coordinates = TRUE
                ) AS first_latitude,

                ARG_MIN(
                    longitude,
                    event_timestamp
                ) FILTER (
                    WHERE has_valid_coordinates = TRUE
                ) AS first_longitude,

                ARG_MAX(
                    latitude,
                    event_timestamp
                ) FILTER (
                    WHERE has_valid_coordinates = TRUE
                ) AS last_latitude,

                ARG_MAX(
                    longitude,
                    event_timestamp
                ) FILTER (
                    WHERE has_valid_coordinates = TRUE
                ) AS last_longitude

            FROM {TELEMETRY_GOLD_BASE_VIEW}

            {date_filter}

            GROUP BY
                STRFTIME(
                    event_timestamp,
                    '%Y-%m-%d'
                ),
                device_serial
        )

        SELECT
            event_date,
            device_serial,
            first_event_at,
            last_event_at,
            message_count,
            distinct_message_type_count,
            valid_position_count,
            invalid_position_count,
            low_gps_precision_count,

            ROUND(
                valid_position_count
                * 100.0
                / NULLIF(
                    message_count,
                    0
                ),
                2
            ) AS valid_position_percentage,

            moving_event_count,
            stopped_event_count,
            average_speed,
            average_speed_while_moving,
            maximum_speed,
            average_hdop,
            minimum_hdop,
            maximum_hdop,
            minimum_battery_voltage,
            maximum_battery_voltage,
            average_battery_voltage,
            minimum_internal_battery,
            maximum_internal_battery,
            average_internal_battery,
            first_odometer_total,
            last_odometer_total,

            CASE
                WHEN first_odometer_total IS NULL
                  OR last_odometer_total IS NULL
                THEN NULL

                WHEN last_odometer_total
                   < first_odometer_total
                THEN NULL

                ELSE
                    last_odometer_total
                    - first_odometer_total
            END AS odometer_delta_raw,

            CASE
                WHEN first_odometer_total IS NULL
                  OR last_odometer_total IS NULL
                THEN FALSE

                WHEN last_odometer_total
                   < first_odometer_total
                THEN TRUE

                ELSE FALSE
            END AS has_odometer_regression,

            first_valid_position_at,
            last_valid_position_at,
            first_latitude,
            first_longitude,
            last_latitude,
            last_longitude

        FROM daily_aggregated

        ORDER BY
            event_date,
            device_serial
        """
    ).to_arrow_table()
