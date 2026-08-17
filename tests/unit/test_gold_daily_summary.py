import duckdb
import pandas as pd

from queo_data_platform.gold.base import (
    SILVER_IDENTITY_RELATION,
    SILVER_TELEMETRY_RELATION,
    create_gold_base_views,
)
from queo_data_platform.gold.daily_summary import (
    build_device_daily_summary,
)


def build_telemetry_row(
    *,
    device_serial: str = "1001",
    event_timestamp: str = "2026-08-17 10:00:00",
    server_timestamp: str = "2026-08-17 10:00:01",
    message_type: str = "T2",
    serial_count: int = 1,
    latitude: float | None = -3.7319,
    longitude: float | None = -38.5267,
    speed: float | None = 20.0,
    hdop: float | None = 1.2,
    battery_voltage: float | None = 12.5,
    internal_battery: float | None = 4.1,
    odometer_total: float | None = 20000.0,
    has_valid_coordinates: bool = True,
    position_quality: str = "VALID",
    source_file: str = "telemetry.csv",
) -> dict[str, object]:
    return {
        "device_serial": device_serial,
        "event_timestamp": pd.Timestamp(event_timestamp),
        "server_timestamp": pd.Timestamp(server_timestamp),
        "message_type": message_type,
        "serial_count": serial_count,
        "latitude": latitude,
        "longitude": longitude,
        "speed": speed,
        "hdop": hdop,
        "battery_voltage": battery_voltage,
        "internal_battery": internal_battery,
        "odometer_total": odometer_total,
        "has_valid_coordinates": (has_valid_coordinates),
        "position_quality": position_quality,
        "source_file": source_file,
    }


def register_gold_sources(
    connection: duckdb.DuckDBPyConnection,
    telemetry_rows: list[dict[str, object]],
) -> None:
    telemetry = pd.DataFrame(telemetry_rows)

    identity = pd.DataFrame(
        [
            {
                "device_serial": "identity-device",
                "event_timestamp": pd.Timestamp("2026-08-17 09:00:00"),
                "server_timestamp": pd.Timestamp("2026-08-17 09:00:01"),
                "imei": "123456789012345",
                "imsi": "724000000000001",
                "iccid": "8955000000000000001",
                "source_file": "identity.csv",
            }
        ]
    )

    connection.register(
        SILVER_TELEMETRY_RELATION,
        telemetry,
    )

    connection.register(
        SILVER_IDENTITY_RELATION,
        identity,
    )

    create_gold_base_views(connection)


def test_daily_summary_aggregates_device_day() -> None:
    connection = duckdb.connect()

    try:
        register_gold_sources(
            connection,
            [
                build_telemetry_row(
                    event_timestamp=("2026-08-17 10:00:00"),
                    serial_count=1,
                    speed=10.0,
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-17 11:00:00"),
                    serial_count=2,
                    speed=20.0,
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-17 12:00:00"),
                    serial_count=3,
                    speed=30.0,
                ),
            ],
        )

        result = build_device_daily_summary(connection).to_pandas()

        assert len(result) == 1

        row = result.iloc[0]

        assert row["event_date"] == "2026-08-17"
        assert row["device_serial"] == "1001"

        assert row["message_count"] == 3

        assert row["first_event_at"] == pd.Timestamp("2026-08-17 10:00:00")

        assert row["last_event_at"] == pd.Timestamp("2026-08-17 12:00:00")

        assert row["average_speed"] == 20.0
        assert row["maximum_speed"] == 30.0

    finally:
        connection.close()


def test_daily_summary_tracks_position_quality() -> None:
    connection = duckdb.connect()

    try:
        register_gold_sources(
            connection,
            [
                build_telemetry_row(
                    serial_count=1,
                    has_valid_coordinates=True,
                    position_quality="VALID",
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-17 11:00:00"),
                    serial_count=2,
                    has_valid_coordinates=True,
                    position_quality=("LOW_GPS_PRECISION"),
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-17 12:00:00"),
                    serial_count=3,
                    has_valid_coordinates=False,
                    position_quality=("INVALID_COORDINATES"),
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-17 13:00:00"),
                    serial_count=4,
                    has_valid_coordinates=False,
                    position_quality=("MISSING_COORDINATES"),
                ),
            ],
        )

        result = build_device_daily_summary(connection).to_pandas()

        row = result.iloc[0]

        assert row["message_count"] == 4
        assert row["valid_position_count"] == 2
        assert row["invalid_position_count"] == 2

        assert row["low_gps_precision_count"] == 1

        assert row["valid_position_percentage"] == 50.0

    finally:
        connection.close()


def test_daily_summary_tracks_movement() -> None:
    connection = duckdb.connect()

    try:
        register_gold_sources(
            connection,
            [
                build_telemetry_row(
                    serial_count=1,
                    speed=0.0,
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-17 11:00:00"),
                    serial_count=2,
                    speed=4.9,
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-17 12:00:00"),
                    serial_count=3,
                    speed=5.0,
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-17 13:00:00"),
                    serial_count=4,
                    speed=15.0,
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-17 14:00:00"),
                    serial_count=5,
                    speed=None,
                ),
            ],
        )

        result = build_device_daily_summary(connection).to_pandas()

        row = result.iloc[0]

        assert row["moving_event_count"] == 2
        assert row["stopped_event_count"] == 2

        assert row["average_speed_while_moving"] == 10.0

        assert row["maximum_speed"] == 15.0

    finally:
        connection.close()


def test_daily_summary_calculates_odometer_delta() -> None:
    connection = duckdb.connect()

    try:
        register_gold_sources(
            connection,
            [
                build_telemetry_row(
                    event_timestamp=("2026-08-17 08:00:00"),
                    serial_count=1,
                    odometer_total=1000.0,
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-17 18:00:00"),
                    serial_count=2,
                    odometer_total=1125.5,
                ),
            ],
        )

        result = build_device_daily_summary(connection).to_pandas()

        row = result.iloc[0]

        assert row["first_odometer_total"] == 1000.0

        assert row["last_odometer_total"] == 1125.5

        assert row["odometer_delta_raw"] == 125.5

        assert not bool(row["has_odometer_regression"])

    finally:
        connection.close()


def test_daily_summary_detects_odometer_regression() -> None:
    connection = duckdb.connect()

    try:
        register_gold_sources(
            connection,
            [
                build_telemetry_row(
                    event_timestamp=("2026-08-17 08:00:00"),
                    serial_count=1,
                    odometer_total=2000.0,
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-17 18:00:00"),
                    serial_count=2,
                    odometer_total=1500.0,
                ),
            ],
        )

        result = build_device_daily_summary(connection).to_pandas()

        row = result.iloc[0]

        assert pd.isna(row["odometer_delta_raw"])

        assert bool(row["has_odometer_regression"])

    finally:
        connection.close()


def test_daily_summary_tracks_first_and_last_valid_position() -> None:
    connection = duckdb.connect()

    try:
        register_gold_sources(
            connection,
            [
                build_telemetry_row(
                    event_timestamp=("2026-08-17 08:00:00"),
                    serial_count=1,
                    latitude=100.0,
                    longitude=200.0,
                    has_valid_coordinates=False,
                    position_quality=("INVALID_COORDINATES"),
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-17 09:00:00"),
                    serial_count=2,
                    latitude=-3.70,
                    longitude=-38.50,
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-17 17:00:00"),
                    serial_count=3,
                    latitude=-3.80,
                    longitude=-38.60,
                ),
            ],
        )

        result = build_device_daily_summary(connection).to_pandas()

        row = result.iloc[0]

        assert row["first_valid_position_at"] == pd.Timestamp("2026-08-17 09:00:00")

        assert row["last_valid_position_at"] == pd.Timestamp("2026-08-17 17:00:00")

        assert row["first_latitude"] == -3.70
        assert row["first_longitude"] == -38.50

        assert row["last_latitude"] == -3.80
        assert row["last_longitude"] == -38.60

    finally:
        connection.close()


def test_daily_summary_can_filter_affected_dates() -> None:
    connection = duckdb.connect()

    try:
        register_gold_sources(
            connection,
            [
                build_telemetry_row(
                    event_timestamp=("2026-08-17 10:00:00"),
                    serial_count=1,
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-18 10:00:00"),
                    serial_count=2,
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-19 10:00:00"),
                    serial_count=3,
                ),
            ],
        )

        result = build_device_daily_summary(
            connection,
            event_dates=("2026-08-18",),
        ).to_pandas()

        assert len(result) == 1

        assert result["event_date"].tolist() == ["2026-08-18"]

    finally:
        connection.close()
