import duckdb
import pandas as pd
import pyarrow as pa

from queo_data_platform.gold.base import (
    TELEMETRY_GOLD_BASE_VIEW,
)


def register_affected_position_devices(
    connection: duckdb.DuckDBPyConnection,
    affected_devices: tuple[str, ...],
) -> None:
    """
    Registra os dispositivos que precisam ter
    a última posição recalculada.
    """

    connection.register(
        "affected_position_devices",
        pd.DataFrame({"device_serial": list(affected_devices)}),
    )


def build_device_last_position(
    connection: duckdb.DuckDBPyConnection,
    affected_devices: tuple[str, ...] | None = None,
) -> pa.Table:
    """
    Constrói o produto Gold device_last_position.

    Retorna no máximo uma posição válida por dispositivo.

    affected_devices=None:
        considera todos os dispositivos.

    affected_devices=(...):
        recalcula somente os dispositivos informados.
    """

    if affected_devices is not None:
        register_affected_position_devices(
            connection,
            affected_devices,
        )

        device_filter = """
            AND device_serial IN (
                SELECT device_serial
                FROM affected_position_devices
            )
        """

    else:
        device_filter = ""

    return connection.execute(
        f"""
        SELECT
            device_serial,

            STRFTIME(
                event_timestamp,
                '%Y-%m-%d'
            ) AS last_position_date,

            event_timestamp
                AS last_position_at,

            server_timestamp
                AS received_at,

            latitude,
            longitude,
            speed,
            direction_degrees,
            battery_voltage,
            internal_battery,
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

          {device_filter}

        QUALIFY
            ROW_NUMBER() OVER (
                PARTITION BY device_serial

                ORDER BY
                    event_timestamp DESC,

                    server_timestamp
                        DESC NULLS LAST,

                    serial_count
                        DESC NULLS LAST
            ) = 1

        ORDER BY device_serial
        """
    ).to_arrow_table()
