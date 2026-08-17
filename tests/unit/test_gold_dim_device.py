import duckdb
import pandas as pd

from queo_data_platform.gold.base import (
    SILVER_IDENTITY_RELATION,
    SILVER_TELEMETRY_RELATION,
    create_gold_base_views,
)
from queo_data_platform.gold.dim_device import (
    build_dim_device,
)


def register_gold_sources(
    connection: duckdb.DuckDBPyConnection,
    *,
    telemetry: pd.DataFrame,
    identity: pd.DataFrame,
) -> None:
    connection.register(
        SILVER_TELEMETRY_RELATION,
        telemetry,
    )

    connection.register(
        SILVER_IDENTITY_RELATION,
        identity,
    )

    create_gold_base_views(connection)


def build_telemetry(
    rows: list[dict[str, object]],
) -> pd.DataFrame:
    return pd.DataFrame(rows)


def build_identity(
    rows: list[dict[str, object]],
) -> pd.DataFrame:
    return pd.DataFrame(rows)


def test_dim_device_combines_identity_and_telemetry() -> None:
    connection = duckdb.connect()

    try:
        telemetry = build_telemetry(
            [
                {
                    "device_serial": "1001",
                    "event_timestamp": pd.Timestamp("2026-08-17 10:00:00"),
                    "server_timestamp": pd.Timestamp("2026-08-17 10:00:01"),
                    "message_type": "T2",
                    "serial_count": 1,
                    "latitude": -3.73,
                    "longitude": -38.52,
                    "speed": 20.0,
                    "protocol_version": "2",
                    "source_file": "telemetry.csv",
                }
            ]
        )

        identity = build_identity(
            [
                {
                    "device_serial": "1001",
                    "event_timestamp": pd.Timestamp("2026-08-17 09:00:00"),
                    "server_timestamp": pd.Timestamp("2026-08-17 09:00:01"),
                    "imei": "123456789012345",
                    "imsi": "724000000000001",
                    "iccid": "8955000000000000001",
                    "identity_auxiliary": "aux",
                    "protocol_version": "1",
                    "has_valid_imei_format": True,
                    "has_valid_imsi_format": True,
                    "has_valid_iccid_format": True,
                    "source_file": "identity.csv",
                }
            ]
        )

        register_gold_sources(
            connection,
            telemetry=telemetry,
            identity=identity,
        )

        result = build_dim_device(connection).to_pandas()

        assert len(result) == 1

        row = result.iloc[0]

        assert row["device_serial"] == "1001"

        assert row["current_imei"] == "123456789012345"

        assert row["identity_event_count"] == 1
        assert row["telemetry_event_count"] == 1

        assert bool(row["has_identity_event"])

        assert bool(row["has_telemetry_event"])

    finally:
        connection.close()


def test_dim_device_uses_latest_identity() -> None:
    connection = duckdb.connect()

    try:
        telemetry = build_telemetry(
            [
                {
                    "device_serial": "1001",
                    "event_timestamp": pd.Timestamp("2026-08-17 12:00:00"),
                    "server_timestamp": pd.Timestamp("2026-08-17 12:00:01"),
                    "message_type": "T2",
                    "serial_count": 1,
                    "latitude": -3.73,
                    "longitude": -38.52,
                    "speed": 20.0,
                    "protocol_version": "3",
                    "source_file": "telemetry.csv",
                }
            ]
        )

        identity = build_identity(
            [
                {
                    "device_serial": "1001",
                    "event_timestamp": pd.Timestamp("2026-08-16 09:00:00"),
                    "server_timestamp": pd.Timestamp("2026-08-16 09:00:01"),
                    "imei": "111111111111111",
                    "imsi": "724000000000001",
                    "iccid": "8955000000000000001",
                    "identity_auxiliary": "old",
                    "protocol_version": "1",
                    "has_valid_imei_format": True,
                    "has_valid_imsi_format": True,
                    "has_valid_iccid_format": True,
                    "source_file": "old.csv",
                },
                {
                    "device_serial": "1001",
                    "event_timestamp": pd.Timestamp("2026-08-17 09:00:00"),
                    "server_timestamp": pd.Timestamp("2026-08-17 09:00:01"),
                    "imei": "222222222222222",
                    "imsi": "724000000000002",
                    "iccid": "8955000000000000002",
                    "identity_auxiliary": "new",
                    "protocol_version": "2",
                    "has_valid_imei_format": True,
                    "has_valid_imsi_format": True,
                    "has_valid_iccid_format": True,
                    "source_file": "new.csv",
                },
            ]
        )

        register_gold_sources(
            connection,
            telemetry=telemetry,
            identity=identity,
        )

        result = build_dim_device(connection).to_pandas()

        row = result.iloc[0]

        assert row["current_imei"] == "222222222222222"

        assert row["current_imsi"] == "724000000000002"

        assert row["current_iccid"] == "8955000000000000002"

        assert row["current_identity_auxiliary"] == "new"

        assert row["identity_event_count"] == 2

    finally:
        connection.close()


def test_dim_device_supports_telemetry_only_device() -> None:
    connection = duckdb.connect()

    try:
        telemetry = build_telemetry(
            [
                {
                    "device_serial": "2001",
                    "event_timestamp": pd.Timestamp("2026-08-17 10:00:00"),
                    "server_timestamp": pd.Timestamp("2026-08-17 10:00:01"),
                    "message_type": "T2",
                    "serial_count": 1,
                    "latitude": -3.73,
                    "longitude": -38.52,
                    "speed": 10.0,
                    "protocol_version": "5",
                    "source_file": "telemetry.csv",
                }
            ]
        )

        identity = build_identity(
            [
                {
                    "device_serial": "other",
                    "event_timestamp": pd.Timestamp("2026-08-17 09:00:00"),
                    "server_timestamp": pd.Timestamp("2026-08-17 09:00:01"),
                    "imei": "123456789012345",
                    "imsi": "724000000000001",
                    "iccid": "8955000000000000001",
                    "identity_auxiliary": None,
                    "protocol_version": "1",
                    "has_valid_imei_format": True,
                    "has_valid_imsi_format": True,
                    "has_valid_iccid_format": True,
                    "source_file": "identity.csv",
                }
            ]
        )

        register_gold_sources(
            connection,
            telemetry=telemetry,
            identity=identity,
        )

        result = build_dim_device(connection).to_pandas()

        device = result.loc[result["device_serial"] == "2001"].iloc[0]

        assert device["identity_event_count"] == 0

        assert device["telemetry_event_count"] == 1

        assert not bool(device["has_identity_event"])

        assert bool(device["has_telemetry_event"])

        assert device["current_protocol_version"] == "5"

    finally:
        connection.close()


def test_dim_device_tracks_first_and_last_activity() -> None:
    connection = duckdb.connect()

    try:
        telemetry = build_telemetry(
            [
                {
                    "device_serial": "1001",
                    "event_timestamp": pd.Timestamp("2026-08-18 18:00:00"),
                    "server_timestamp": pd.Timestamp("2026-08-18 18:00:01"),
                    "message_type": "T2",
                    "serial_count": 1,
                    "latitude": -3.73,
                    "longitude": -38.52,
                    "speed": 10.0,
                    "protocol_version": "2",
                    "source_file": "telemetry.csv",
                }
            ]
        )

        identity = build_identity(
            [
                {
                    "device_serial": "1001",
                    "event_timestamp": pd.Timestamp("2026-08-16 08:00:00"),
                    "server_timestamp": pd.Timestamp("2026-08-16 08:00:01"),
                    "imei": "123456789012345",
                    "imsi": "724000000000001",
                    "iccid": "8955000000000000001",
                    "identity_auxiliary": None,
                    "protocol_version": "1",
                    "has_valid_imei_format": True,
                    "has_valid_imsi_format": True,
                    "has_valid_iccid_format": True,
                    "source_file": "identity.csv",
                }
            ]
        )

        register_gold_sources(
            connection,
            telemetry=telemetry,
            identity=identity,
        )

        result = build_dim_device(connection).to_pandas()

        row = result.iloc[0]

        assert row["first_seen_at"] == pd.Timestamp("2026-08-16 08:00:00")

        assert row["last_seen_at"] == pd.Timestamp("2026-08-18 18:00:00")

        assert row["first_identity_at"] == pd.Timestamp("2026-08-16 08:00:00")

        assert row["last_telemetry_at"] == pd.Timestamp("2026-08-18 18:00:00")

    finally:
        connection.close()


def test_dim_device_can_rebuild_only_affected_devices() -> None:
    connection = duckdb.connect()

    try:
        telemetry = build_telemetry(
            [
                {
                    "device_serial": "1001",
                    "event_timestamp": pd.Timestamp("2026-08-17 10:00:00"),
                    "server_timestamp": pd.Timestamp("2026-08-17 10:00:01"),
                    "message_type": "T2",
                    "serial_count": 1,
                    "latitude": -3.73,
                    "longitude": -38.52,
                    "speed": 10.0,
                    "protocol_version": "1",
                    "source_file": "a.csv",
                },
                {
                    "device_serial": "2002",
                    "event_timestamp": pd.Timestamp("2026-08-17 11:00:00"),
                    "server_timestamp": pd.Timestamp("2026-08-17 11:00:01"),
                    "message_type": "T2",
                    "serial_count": 1,
                    "latitude": -3.74,
                    "longitude": -38.53,
                    "speed": 20.0,
                    "protocol_version": "1",
                    "source_file": "b.csv",
                },
            ]
        )

        identity = build_identity(
            [
                {
                    "device_serial": "1001",
                    "event_timestamp": pd.Timestamp("2026-08-17 09:00:00"),
                    "server_timestamp": pd.Timestamp("2026-08-17 09:00:01"),
                    "imei": "123456789012345",
                    "imsi": "724000000000001",
                    "iccid": "8955000000000000001",
                    "identity_auxiliary": None,
                    "protocol_version": "1",
                    "has_valid_imei_format": True,
                    "has_valid_imsi_format": True,
                    "has_valid_iccid_format": True,
                    "source_file": "identity.csv",
                }
            ]
        )

        register_gold_sources(
            connection,
            telemetry=telemetry,
            identity=identity,
        )

        result = build_dim_device(
            connection,
            affected_devices=("2002",),
        ).to_pandas()

        assert result["device_serial"].tolist() == ["2002"]

    finally:
        connection.close()
