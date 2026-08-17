from datetime import datetime
from pathlib import Path
from typing import Literal

import pyarrow as pa
from deltalake import DeltaTable, write_deltalake

from queo_data_platform.contracts.gold import (
    DATA_QUALITY_SUMMARY_TABLE_NAME,
    DEVICE_DAILY_SUMMARY_TABLE_NAME,
    DEVICE_LAST_POSITION_TABLE_NAME,
    DEVICE_ROUTE_POINTS_TABLE_NAME,
    DIM_DEVICE_TABLE_NAME,
)
from queo_data_platform.contracts.silver import (
    DEVICE_IDENTITY_SCHEMA,
    DEVICE_IDENTITY_TABLE_NAME,
    REJECTED_LOGS_SCHEMA,
    REJECTED_LOGS_TABLE_NAME,
    TELEMETRY_SCHEMA,
    TELEMETRY_TABLE_NAME,
)
from queo_data_platform.gold.service import load_gold_data
from queo_data_platform.silver.service import SilverLoadResult


def write_silver_table(
    table_path: Path,
    rows: list[dict[str, object]],
    *,
    schema: pa.Schema,
    partition_by: str,
    mode: Literal[
        "overwrite",
        "append",
    ] = "overwrite",
) -> None:
    table_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    table = pa.Table.from_pylist(
        rows,
        schema=schema,
    )

    if mode == "append":
        write_deltalake(
            table_path,
            table,
            mode="append",
        )
    else:
        write_deltalake(
            table_path,
            table,
            mode="overwrite",
            partition_by=[partition_by],
        )


def parse_timestamp(
    event_date: str,
    event_time: str,
) -> datetime:
    return datetime.fromisoformat(f"{event_date}T{event_time}")


def build_telemetry_row(
    *,
    row_id: str,
    device_serial: str,
    event_date: str,
    event_time: str,
    serial_count: int,
    latitude: float = -3.7319,
    longitude: float = -38.5267,
    speed: float = 20.0,
) -> dict[str, object]:
    event_timestamp = parse_timestamp(
        event_date,
        event_time,
    )

    return {
        "event_date": event_date,
        "server_timestamp": event_timestamp,
        "device_timestamp": event_timestamp,
        "event_timestamp": event_timestamp,
        "log_type": "tracker",
        "message_type": "T2",
        "report_type": 1,
        "protocol_version": "1",
        "device_serial": device_serial,
        "terminal_status": "OK",
        "battery_voltage": 12.5,
        "location_status": "A",
        "latitude": latitude,
        "longitude": longitude,
        "speed": speed,
        "direction_degrees": 180.0,
        "internal_battery": 4.1,
        "odometer_trip": 100.0,
        "odometer_total": 20000.0,
        "horimeter": 1500.0,
        "hdop": 1.2,
        "mcc": "724",
        "mnc": "05",
        "lac": "100",
        "cell_id": "200",
        "rx_level": -70.0,
        "serial_count": serial_count,
        "transmission_technology": "GPRS",
        "message_group": "G1",
        "io_status": "0",
        "driver_id": None,
        "passenger_id": None,
        "rpm": 2500.0,
        "tachograph_speed": 20.0,
        "tachograph_odometer": 20000.0,
        "temperature_1": 25.0,
        "temperature_2": None,
        "temperature_3": None,
        "temperature_4": None,
        "source_file": "tracker.csv",
        "source_file_hash": "hash",
        "source_row_number": serial_count,
        "row_id": row_id,
        "batch_id": "batch",
        "ingested_at": None,
        "ingestion_date": None,
        "has_valid_coordinates": True,
        "position_quality": "VALID",
    }


def build_identity_row(
    *,
    row_id: str,
    device_serial: str,
    event_date: str,
) -> dict[str, object]:
    event_timestamp = parse_timestamp(
        event_date,
        "09:00:00",
    )

    return {
        "event_date": event_date,
        "server_timestamp": event_timestamp,
        "device_timestamp": event_timestamp,
        "event_timestamp": event_timestamp,
        "message_type": "T1",
        "report_type": 1,
        "protocol_version": "1",
        "device_serial_raw": f"M{device_serial}",
        "device_serial": device_serial,
        "iccid": "8955000000000000001",
        "identity_auxiliary": "aux",
        "imsi": "724000000000001",
        "imei": "359000000000001",
        "source_file": "identity.csv",
        "source_file_hash": "identity-hash",
        "source_row_number": 1,
        "row_id": row_id,
        "batch_id": "batch",
        "ingested_at": None,
        "ingestion_date": None,
        "has_valid_iccid_format": True,
        "has_valid_imsi_format": True,
        "has_valid_imei_format": True,
    }


def build_rejected_row(
    *,
    row_id: str,
    rejection_date: str,
) -> dict[str, object]:
    return {
        "rejection_date": rejection_date,
        "source_file": "rejected.csv",
        "source_file_hash": "rejected-hash",
        "source_row_number": 1,
        "row_id": row_id,
        "batch_id": "batch",
        "rejection_reason": "INVALID_MESSAGE_TYPE",
    }


def create_silver_sources(
    silver_dir: Path,
) -> None:
    write_silver_table(
        silver_dir / TELEMETRY_TABLE_NAME,
        [
            build_telemetry_row(
                row_id="telemetry-17",
                device_serial="1001",
                event_date="2026-08-17",
                event_time="10:00:00",
                serial_count=1,
            ),
            build_telemetry_row(
                row_id="telemetry-18",
                device_serial="1001",
                event_date="2026-08-18",
                event_time="10:00:00",
                serial_count=2,
            ),
        ],
        schema=TELEMETRY_SCHEMA,
        partition_by="event_date",
    )

    write_silver_table(
        silver_dir / DEVICE_IDENTITY_TABLE_NAME,
        [
            build_identity_row(
                row_id="identity-17",
                device_serial="1001",
                event_date="2026-08-17",
            )
        ],
        schema=DEVICE_IDENTITY_SCHEMA,
        partition_by="event_date",
    )

    write_silver_table(
        silver_dir / REJECTED_LOGS_TABLE_NAME,
        [
            build_rejected_row(
                row_id="rejected-17",
                rejection_date="2026-08-17",
            )
        ],
        schema=REJECTED_LOGS_SCHEMA,
        partition_by="rejection_date",
    )


def test_full_gold_build_creates_all_products(
    tmp_path: Path,
) -> None:
    silver_dir = tmp_path / "02_silver"
    gold_dir = tmp_path / "03_gold"

    create_silver_sources(silver_dir)

    result = load_gold_data(
        silver_dir=silver_dir,
        gold_dir=gold_dir,
    )

    assert result.mode == "FULL"

    assert result.affected_event_dates == (
        "2026-08-17",
        "2026-08-18",
    )

    assert result.affected_devices == ("1001",)

    for table_name in (
        DIM_DEVICE_TABLE_NAME,
        DEVICE_LAST_POSITION_TABLE_NAME,
        DEVICE_ROUTE_POINTS_TABLE_NAME,
        DEVICE_DAILY_SUMMARY_TABLE_NAME,
        DATA_QUALITY_SUMMARY_TABLE_NAME,
    ):
        assert DeltaTable.is_deltatable(str(gold_dir / table_name))


def test_gold_returns_noop_when_silver_has_no_changes(
    tmp_path: Path,
) -> None:
    silver_dir = tmp_path / "02_silver"
    gold_dir = tmp_path / "03_gold"

    create_silver_sources(silver_dir)

    load_gold_data(
        silver_dir=silver_dir,
        gold_dir=gold_dir,
    )

    silver_result = SilverLoadResult(
        mode="NOOP",
        batch_ids=(),
        affected_event_dates=(),
        affected_rejection_dates=(),
        telemetry_rows_written=0,
        identity_rows_written=0,
        rejected_rows_written=0,
    )

    result = load_gold_data(
        silver_dir=silver_dir,
        gold_dir=gold_dir,
        silver_result=silver_result,
    )

    assert result.mode == "NOOP"
    assert not result.has_changes

    assert result.dim_device_rows_written == 0
    assert result.route_points_rows_written == 0


def test_incremental_gold_rebuilds_only_affected_date(
    tmp_path: Path,
) -> None:
    silver_dir = tmp_path / "02_silver"
    gold_dir = tmp_path / "03_gold"

    create_silver_sources(silver_dir)

    load_gold_data(
        silver_dir=silver_dir,
        gold_dir=gold_dir,
    )

    write_silver_table(
        silver_dir / TELEMETRY_TABLE_NAME,
        [
            build_telemetry_row(
                row_id="late-17",
                device_serial="1001",
                event_date="2026-08-17",
                event_time="12:00:00",
                serial_count=3,
                latitude=-3.80,
                longitude=-38.60,
            )
        ],
        schema=TELEMETRY_SCHEMA,
        partition_by="event_date",
        mode="append",
    )

    silver_result = SilverLoadResult(
        mode="INCREMENTAL",
        batch_ids=("batch-new",),
        affected_event_dates=("2026-08-17",),
        affected_rejection_dates=("2026-08-17",),
        telemetry_rows_written=1,
        identity_rows_written=0,
        rejected_rows_written=0,
    )

    result = load_gold_data(
        silver_dir=silver_dir,
        gold_dir=gold_dir,
        silver_result=silver_result,
    )

    assert result.mode == "INCREMENTAL"

    assert result.affected_event_dates == ("2026-08-17",)

    routes = DeltaTable(str(gold_dir / DEVICE_ROUTE_POINTS_TABLE_NAME)).to_pandas()

    day_17 = routes.loc[routes["event_date"] == "2026-08-17"]

    day_18 = routes.loc[routes["event_date"] == "2026-08-18"]

    assert len(day_17) == 2
    assert len(day_18) == 1

    daily = DeltaTable(str(gold_dir / DEVICE_DAILY_SUMMARY_TABLE_NAME)).to_pandas()

    day_17_summary = daily.loc[daily["event_date"] == "2026-08-17"].iloc[0]

    assert day_17_summary["message_count"] == 2
