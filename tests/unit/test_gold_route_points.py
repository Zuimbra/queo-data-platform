import duckdb
import pandas as pd

from queo_data_platform.gold.base import (
    SILVER_IDENTITY_RELATION,
    SILVER_TELEMETRY_RELATION,
    create_gold_base_views,
)
from queo_data_platform.gold.route_points import (
    build_device_route_points,
)


def build_telemetry_row(
    *,
    device_serial: str = "1001",
    event_timestamp: str = "2026-08-17 10:00:00",
    server_timestamp: str = "2026-08-17 10:00:01",
    serial_count: int = 1,
    latitude: float = -3.7319,
    longitude: float = -38.5267,
    speed: float | None = 20.0,
    has_valid_coordinates: bool = True,
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
        "odometer_trip": 100.0,
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


def test_route_points_are_ordered_by_event_time() -> None:
    connection = duckdb.connect()

    try:
        register_gold_sources(
            connection,
            [
                build_telemetry_row(
                    event_timestamp=("2026-08-17 12:00:00"),
                    latitude=-3.80,
                    longitude=-38.60,
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-17 10:00:00"),
                    latitude=-3.70,
                    longitude=-38.50,
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-17 11:00:00"),
                    latitude=-3.75,
                    longitude=-38.55,
                ),
            ],
        )

        result = build_device_route_points(connection).to_pandas()

        assert result["point_sequence"].tolist() == [1, 2, 3]

        assert result["event_timestamp"].tolist() == [
            pd.Timestamp("2026-08-17 10:00:00"),
            pd.Timestamp("2026-08-17 11:00:00"),
            pd.Timestamp("2026-08-17 12:00:00"),
        ]

    finally:
        connection.close()


def test_route_sequence_resets_per_device_and_date() -> None:
    connection = duckdb.connect()

    try:
        register_gold_sources(
            connection,
            [
                build_telemetry_row(
                    device_serial="1001",
                    event_timestamp=("2026-08-17 10:00:00"),
                ),
                build_telemetry_row(
                    device_serial="1001",
                    event_timestamp=("2026-08-17 11:00:00"),
                ),
                build_telemetry_row(
                    device_serial="1001",
                    event_timestamp=("2026-08-18 08:00:00"),
                ),
                build_telemetry_row(
                    device_serial="2002",
                    event_timestamp=("2026-08-17 09:00:00"),
                ),
            ],
        )

        result = build_device_route_points(connection).to_pandas()

        device_1001_day_17 = result.loc[
            (result["device_serial"] == "1001") & (result["event_date"] == "2026-08-17")
        ]

        device_1001_day_18 = result.loc[
            (result["device_serial"] == "1001") & (result["event_date"] == "2026-08-18")
        ]

        device_2002 = result.loc[result["device_serial"] == "2002"]

        assert device_1001_day_17["point_sequence"].tolist() == [1, 2]

        assert device_1001_day_18["point_sequence"].tolist() == [1]

        assert device_2002["point_sequence"].tolist() == [1]

    finally:
        connection.close()


def test_route_points_ignore_invalid_coordinates() -> None:
    connection = duckdb.connect()

    try:
        register_gold_sources(
            connection,
            [
                build_telemetry_row(
                    event_timestamp=("2026-08-17 10:00:00"),
                    has_valid_coordinates=True,
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-17 11:00:00"),
                    latitude=120.0,
                    has_valid_coordinates=False,
                ),
            ],
        )

        result = build_device_route_points(connection).to_pandas()

        assert len(result) == 1

        assert result.iloc[0]["event_timestamp"] == pd.Timestamp("2026-08-17 10:00:00")

    finally:
        connection.close()


def test_route_points_ignore_zero_zero_coordinates() -> None:
    connection = duckdb.connect()

    try:
        register_gold_sources(
            connection,
            [
                build_telemetry_row(
                    latitude=-3.73,
                    longitude=-38.52,
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-17 11:00:00"),
                    latitude=0.0,
                    longitude=0.0,
                    has_valid_coordinates=True,
                ),
            ],
        )

        result = build_device_route_points(connection).to_pandas()

        assert len(result) == 1

        assert result.iloc[0]["latitude"] == -3.73

        assert result.iloc[0]["longitude"] == -38.52

    finally:
        connection.close()


def test_route_points_classify_movement() -> None:
    connection = duckdb.connect()

    try:
        register_gold_sources(
            connection,
            [
                build_telemetry_row(
                    event_timestamp=("2026-08-17 10:00:00"),
                    speed=4.9,
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-17 11:00:00"),
                    speed=5.0,
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-17 12:00:00"),
                    speed=None,
                ),
            ],
        )

        result = build_device_route_points(connection).to_pandas()

        assert result["is_moving"].tolist() == [
            False,
            True,
            False,
        ]

    finally:
        connection.close()


def test_route_points_can_filter_affected_dates() -> None:
    connection = duckdb.connect()

    try:
        register_gold_sources(
            connection,
            [
                build_telemetry_row(
                    event_timestamp=("2026-08-17 10:00:00"),
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-18 10:00:00"),
                ),
                build_telemetry_row(
                    event_timestamp=("2026-08-19 10:00:00"),
                ),
            ],
        )

        result = build_device_route_points(
            connection,
            event_dates=("2026-08-18",),
        ).to_pandas()

        assert len(result) == 1

        assert result["event_date"].tolist() == ["2026-08-18"]

    finally:
        connection.close()
