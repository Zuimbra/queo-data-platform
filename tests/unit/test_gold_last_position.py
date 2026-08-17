import duckdb
import pandas as pd

from queo_data_platform.gold.base import (
    SILVER_IDENTITY_RELATION,
    SILVER_TELEMETRY_RELATION,
    create_gold_base_views,
)
from queo_data_platform.gold.last_position import (
    build_device_last_position,
)


def build_telemetry_row(
    *,
    device_serial: str = "1001",
    event_timestamp: str = "2026-08-17 10:00:00",
    server_timestamp: str = "2026-08-17 10:00:01",
    serial_count: int = 1,
    latitude: float = -3.7319,
    longitude: float = -38.5267,
    has_valid_coordinates: bool = True,
    speed: float = 20.0,
    source_file: str = "telemetry.csv",
) -> dict[str, object]:
    return {
        "device_serial": device_serial,
        "event_timestamp": pd.Timestamp(event_timestamp),
        "server_timestamp": pd.Timestamp(server_timestamp),
        "message_type": "T2",
        "report_type": 1,
        "serial_count": serial_count,
        "latitude": latitude,
        "longitude": longitude,
        "speed": speed,
        "direction_degrees": 180.0,
        "battery_voltage": 12.5,
        "internal_battery": 4.1,
        "odometer_total": 20000.0,
        "horimeter": 1500.0,
        "hdop": 1.2,
        "rx_level": -70.0,
        "protocol_version": "1",
        "position_quality": "VALID",
        "has_valid_coordinates": (has_valid_coordinates),
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


def test_last_position_selects_latest_event() -> None:
    connection = duckdb.connect()

    try:
        register_gold_sources(
            connection,
            [
                build_telemetry_row(
                    event_timestamp=("2026-08-17 10:00:00"),
                    latitude=-3.70,
                    longitude=-38.50,
                    source_file="old.csv",
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-17 12:00:00"),
                    latitude=-3.80,
                    longitude=-38.60,
                    source_file="new.csv",
                ),
            ],
        )

        result = build_device_last_position(connection).to_pandas()

        assert len(result) == 1

        row = result.iloc[0]

        assert row["last_position_at"] == pd.Timestamp("2026-08-17 12:00:00")

        assert row["latitude"] == -3.80
        assert row["longitude"] == -38.60

        assert row["source_file"] == "new.csv"

    finally:
        connection.close()


def test_last_position_ignores_invalid_coordinates() -> None:
    connection = duckdb.connect()

    try:
        register_gold_sources(
            connection,
            [
                build_telemetry_row(
                    event_timestamp=("2026-08-17 10:00:00"),
                    latitude=-3.73,
                    longitude=-38.52,
                    has_valid_coordinates=True,
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-17 12:00:00"),
                    latitude=120.0,
                    longitude=-38.52,
                    has_valid_coordinates=False,
                ),
            ],
        )

        result = build_device_last_position(connection).to_pandas()

        row = result.iloc[0]

        assert row["last_position_at"] == pd.Timestamp("2026-08-17 10:00:00")

        assert row["latitude"] == -3.73

    finally:
        connection.close()


def test_last_position_ignores_zero_zero_coordinates() -> None:
    connection = duckdb.connect()

    try:
        register_gold_sources(
            connection,
            [
                build_telemetry_row(
                    event_timestamp=("2026-08-17 10:00:00"),
                    latitude=-3.73,
                    longitude=-38.52,
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-17 12:00:00"),
                    latitude=0.0,
                    longitude=0.0,
                    has_valid_coordinates=True,
                ),
            ],
        )

        result = build_device_last_position(connection).to_pandas()

        row = result.iloc[0]

        assert row["latitude"] == -3.73
        assert row["longitude"] == -38.52

        assert row["last_position_at"] == pd.Timestamp("2026-08-17 10:00:00")

    finally:
        connection.close()


def test_last_position_uses_server_timestamp_as_tiebreaker() -> None:
    connection = duckdb.connect()

    try:
        register_gold_sources(
            connection,
            [
                build_telemetry_row(
                    event_timestamp=("2026-08-17 10:00:00"),
                    server_timestamp=("2026-08-17 10:00:01"),
                    serial_count=10,
                    latitude=-3.70,
                    longitude=-38.50,
                    source_file="old.csv",
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-17 10:00:00"),
                    server_timestamp=("2026-08-17 10:00:05"),
                    serial_count=10,
                    latitude=-3.80,
                    longitude=-38.60,
                    source_file="new.csv",
                ),
            ],
        )

        result = build_device_last_position(connection).to_pandas()

        row = result.iloc[0]

        assert row["received_at"] == pd.Timestamp("2026-08-17 10:00:05")

        assert row["latitude"] == -3.80
        assert row["longitude"] == -38.60

    finally:
        connection.close()


def test_last_position_can_filter_affected_devices() -> None:
    connection = duckdb.connect()

    try:
        register_gold_sources(
            connection,
            [
                build_telemetry_row(
                    device_serial="1001",
                    latitude=-3.70,
                    longitude=-38.50,
                ),
                build_telemetry_row(
                    device_serial="2002",
                    latitude=-3.80,
                    longitude=-38.60,
                ),
            ],
        )

        result = build_device_last_position(
            connection,
            affected_devices=("2002",),
        ).to_pandas()

        assert result["device_serial"].tolist() == ["2002"]

    finally:
        connection.close()


def test_last_position_preserves_position_metrics() -> None:
    connection = duckdb.connect()

    try:
        register_gold_sources(
            connection,
            [
                build_telemetry_row(
                    device_serial="1001",
                )
            ],
        )

        result = build_device_last_position(connection).to_pandas()

        row = result.iloc[0]

        assert row["speed"] == 20.0

        assert row["direction_degrees"] == 180.0

        assert row["battery_voltage"] == 12.5

        assert row["internal_battery"] == 4.1

        assert row["odometer_total"] == 20000.0

        assert row["horimeter"] == 1500.0
        assert row["hdop"] == 1.2
        assert row["rx_level"] == -70.0

        assert row["position_quality"] == "VALID"

    finally:
        connection.close()
