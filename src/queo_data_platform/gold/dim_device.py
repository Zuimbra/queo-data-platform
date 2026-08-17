import duckdb
import pandas as pd
import pyarrow as pa

from queo_data_platform.gold.base import (
    IDENTITY_GOLD_BASE_VIEW,
    TELEMETRY_GOLD_BASE_VIEW,
)


def register_affected_devices(
    connection: duckdb.DuckDBPyConnection,
    affected_devices: tuple[str, ...],
) -> None:
    """
    Registra os dispositivos afetados para processamento
    incremental da dimensão.
    """

    connection.register(
        "affected_gold_devices",
        pd.DataFrame({"device_serial": list(affected_devices)}),
    )


def build_dim_device(
    connection: duckdb.DuckDBPyConnection,
    affected_devices: tuple[str, ...] | None = None,
) -> pa.Table:
    """
    Constrói a dimensão Gold de dispositivos.

    affected_devices=None:
        processa todos os dispositivos.

    affected_devices=(...):
        recalcula somente os dispositivos informados.
    """

    if affected_devices is not None:
        register_affected_devices(
            connection,
            affected_devices,
        )

        device_filter = """
            WHERE devices.device_serial IN (
                SELECT device_serial
                FROM affected_gold_devices
            )
        """

    else:
        device_filter = ""

    return connection.execute(
        f"""
        WITH identity_summary AS (
            SELECT
                device_serial,

                MIN(event_timestamp)
                    AS first_identity_at,

                MAX(event_timestamp)
                    AS last_identity_at,

                COUNT(*)
                    AS identity_event_count,

                ARG_MAX(
                    imei,
                    event_timestamp
                ) AS current_imei,

                ARG_MAX(
                    imsi,
                    event_timestamp
                ) AS current_imsi,

                ARG_MAX(
                    iccid,
                    event_timestamp
                ) AS current_iccid,

                ARG_MAX(
                    identity_auxiliary,
                    event_timestamp
                ) AS current_identity_auxiliary,

                ARG_MAX(
                    protocol_version,
                    event_timestamp
                ) AS current_protocol_version,

                ARG_MAX(
                    has_valid_imei_format,
                    event_timestamp
                ) AS current_imei_format_valid,

                ARG_MAX(
                    has_valid_imsi_format,
                    event_timestamp
                ) AS current_imsi_format_valid,

                ARG_MAX(
                    has_valid_iccid_format,
                    event_timestamp
                ) AS current_iccid_format_valid

            FROM {IDENTITY_GOLD_BASE_VIEW}

            GROUP BY device_serial
        ),

        telemetry_summary AS (
            SELECT
                device_serial,

                MIN(event_timestamp)
                    AS first_telemetry_at,

                MAX(event_timestamp)
                    AS last_telemetry_at,

                COUNT(*)
                    AS telemetry_event_count,

                ARG_MAX(
                    protocol_version,
                    event_timestamp
                ) AS latest_telemetry_protocol_version

            FROM {TELEMETRY_GOLD_BASE_VIEW}

            GROUP BY device_serial
        ),

        all_activity AS (
            SELECT
                device_serial,
                event_timestamp

            FROM {IDENTITY_GOLD_BASE_VIEW}

            UNION ALL

            SELECT
                device_serial,
                event_timestamp

            FROM {TELEMETRY_GOLD_BASE_VIEW}
        ),

        activity_summary AS (
            SELECT
                device_serial,

                MIN(event_timestamp)
                    AS first_seen_at,

                MAX(event_timestamp)
                    AS last_seen_at

            FROM all_activity

            GROUP BY device_serial
        ),

        devices AS (
            SELECT
                device_serial

            FROM {IDENTITY_GOLD_BASE_VIEW}

            UNION

            SELECT
                device_serial

            FROM {TELEMETRY_GOLD_BASE_VIEW}
        )

        SELECT
            devices.device_serial,

            identity_summary.current_imei,
            identity_summary.current_imsi,
            identity_summary.current_iccid,
            identity_summary.current_identity_auxiliary,

            COALESCE(
                identity_summary.current_protocol_version,
                telemetry_summary.latest_telemetry_protocol_version
            ) AS current_protocol_version,

            activity_summary.first_seen_at,
            activity_summary.last_seen_at,

            identity_summary.first_identity_at,
            identity_summary.last_identity_at,

            telemetry_summary.first_telemetry_at,
            telemetry_summary.last_telemetry_at,

            COALESCE(
                identity_summary.identity_event_count,
                0
            ) AS identity_event_count,

            COALESCE(
                telemetry_summary.telemetry_event_count,
                0
            ) AS telemetry_event_count,

            COALESCE(
                identity_summary.identity_event_count,
                0
            ) > 0 AS has_identity_event,

            COALESCE(
                telemetry_summary.telemetry_event_count,
                0
            ) > 0 AS has_telemetry_event,

            identity_summary.current_imei_format_valid,
            identity_summary.current_imsi_format_valid,
            identity_summary.current_iccid_format_valid

        FROM devices

        LEFT JOIN identity_summary
            ON devices.device_serial
             = identity_summary.device_serial

        LEFT JOIN telemetry_summary
            ON devices.device_serial
             = telemetry_summary.device_serial

        LEFT JOIN activity_summary
            ON devices.device_serial
             = activity_summary.device_serial

        {device_filter}

        ORDER BY
            devices.device_serial
        """
    ).to_arrow_table()
