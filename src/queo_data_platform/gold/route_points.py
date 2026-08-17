import duckdb
import pandas as pd
import pyarrow as pa

from queo_data_platform.gold.base import (
    TELEMETRY_GOLD_BASE_VIEW,
)


def register_route_dates(
    connection: duckdb.DuckDBPyConnection,
    event_dates: tuple[str, ...],
) -> None:
    """
    Registra as datas que precisam ser reconstruídas
    no produto device_route_points.
    """

    connection.register(
        "route_gold_dates",
        pd.DataFrame({"event_date": list(event_dates)}),
    )


def build_device_route_points(
    connection: duckdb.DuckDBPyConnection,
    event_dates: tuple[str, ...] | None = None,
) -> pa.Table:
    """
    Constrói o produto Gold device_route_points.

    event_dates=None:
        processa todas as datas disponíveis.

    event_dates=(...):
        recalcula somente as datas informadas.
    """

    if event_dates is not None:
        register_route_dates(
            connection,
            event_dates,
        )

        date_filter = """
            AND STRFTIME(
                event_timestamp,
                '%Y-%m-%d'
            ) IN (
                SELECT event_date
                FROM route_gold_dates
            )
        """

    else:
        date_filter = ""

    return connection.execute(
        f"""
        WITH valid_points AS (
            SELECT
                STRFTIME(
                    event_timestamp,
                    '%Y-%m-%d'
                ) AS event_date,

                device_serial,
                event_timestamp,

                server_timestamp
                    AS received_at,

                latitude,
                longitude,
                speed,
                direction_degrees,
                odometer_trip,
                odometer_total,
                horimeter,
                hdop,
                rx_level,
                message_type,
                report_type,
                serial_count,
                protocol_version,
                position_quality,
                source_file

            FROM {TELEMETRY_GOLD_BASE_VIEW}

            WHERE has_valid_coordinates = TRUE

              AND NOT (
                  latitude = 0
                  AND longitude = 0
              )

              {date_filter}
        ),

        ordered_points AS (
            SELECT
                *,

                ROW_NUMBER() OVER (
                    PARTITION BY
                        device_serial,
                        event_date

                    ORDER BY
                        event_timestamp,
                        received_at NULLS LAST,
                        serial_count NULLS LAST
                ) AS point_sequence

            FROM valid_points
        )

        SELECT
            event_date,
            device_serial,
            point_sequence,
            event_timestamp,
            received_at,
            latitude,
            longitude,
            speed,
            direction_degrees,
            odometer_trip,
            odometer_total,
            horimeter,
            hdop,
            rx_level,
            message_type,
            report_type,
            serial_count,
            protocol_version,
            position_quality,

            COALESCE(
                speed,
                0
            ) >= 5 AS is_moving,

            source_file

        FROM ordered_points

        ORDER BY
            event_date,
            device_serial,
            point_sequence
        """
    ).to_arrow_table()
