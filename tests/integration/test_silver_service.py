from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import pandas as pd
import pyarrow as pa
from deltalake import DeltaTable, write_deltalake

from queo_data_platform.config.settings import (
    load_settings,
)
from queo_data_platform.contracts.silver import (
    DEVICE_IDENTITY_TABLE_NAME,
    REJECTED_LOGS_TABLE_NAME,
    TELEMETRY_TABLE_NAME,
)
from queo_data_platform.contracts.tracker import (
    BRONZE_TABLE_NAME,
    RAW_TRACKER_REQUIRED_COLUMNS,
)
from queo_data_platform.silver.service import (
    load_silver,
    load_silver_data,
)


def build_bronze_row(
    *,
    row_id: str,
    batch_id: str,
    event_date: str,
    message_type: str = "T2",
) -> dict[str, object]:
    row: dict[str, object] = {
        column: "value" for column in RAW_TRACKER_REQUIRED_COLUMNS
    }

    row.update(
        {
            "DATA_SERVIDOR": (f"{event_date} 12:00:00"),
            "TM_STAMP": (f"{event_date} 11:59:50"),
            "TIPO_LOG": "tracker",
            "MESS_TYPE": message_type,
            "REPT_TYPE": "1",
            "PRT_VER": "1",
            "S/N ou IMEI": "M123456789",
            "BAT_VOLT": "12.5",
            "LOC_STATUS": "A",
            "LAT": "-3.7319",
            "LONT": "-38.5267",
            "SPEED": "45.5",
            "DIR": "180",
            "INT_BATT": "4.1",
            "ODO_TRIP": "100",
            "ODO_TOTAL": "20000",
            "HORIMETER": "1500",
            "HDOP": "1.2",
            "RX_LEVEL": "-70",
            "SER_COUNT": "15",
            "RPM": "2500",
            "TACHO_SPD": "45",
            "TACHO_ODO": "20000",
            "TEMP_1": "25",
            "TEMP_2": "26",
            "TEMP_3": "27",
            "TEMP_4": "28",
            "source_file": (f"{batch_id}.csv"),
            "source_file_hash": (f"hash-{batch_id}"),
            "source_row_number": 1,
            "row_id": row_id,
            "batch_id": batch_id,
            "ingested_at": datetime(
                2026,
                8,
                17,
                12,
                1,
                tzinfo=UTC,
            ),
            "ingestion_date": event_date,
        }
    )

    return row


def write_bronze_rows(
    bronze_dir: Path,
    rows: list[dict[str, object]],
    *,
    mode: Literal[
        "overwrite",
        "append",
    ] = "overwrite",
) -> None:
    bronze_path = bronze_dir / BRONZE_TABLE_NAME

    bronze_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    dataframe = pd.DataFrame(rows)

    table = pa.Table.from_pandas(
        dataframe,
        preserve_index=False,
    )

    if mode == "append":
        write_deltalake(
            bronze_path,
            table,
            mode="append",
        )

    else:
        write_deltalake(
            bronze_path,
            table,
            mode="overwrite",
        )


def test_full_rebuild_creates_silver_products(
    tmp_path: Path,
) -> None:
    bronze_dir = tmp_path / "01_bronze"

    silver_dir = tmp_path / "02_silver"

    telemetry_row = build_bronze_row(
        row_id="telemetry-1",
        batch_id="batch-001",
        event_date="2026-08-17",
    )

    identity_row = build_bronze_row(
        row_id="identity-1",
        batch_id="batch-001",
        event_date="2026-08-17",
        message_type="T1",
    )

    # T1 reutiliza esses campos como identificadores.
    identity_row["BAT_VOLT"] = "8955000000000000001"

    identity_row["LAT"] = "724000000000001"

    identity_row["LONT"] = "359000000000001"

    rejected_row = build_bronze_row(
        row_id="rejected-1",
        batch_id="batch-001",
        event_date="2026-08-17",
        message_type="INVALID",
    )

    write_bronze_rows(
        bronze_dir,
        [
            telemetry_row,
            identity_row,
            rejected_row,
        ],
    )

    result = load_silver_data(
        bronze_dir=bronze_dir,
        silver_dir=silver_dir,
    )

    assert result.mode == "FULL"

    assert result.telemetry_rows_written == 1
    assert result.identity_rows_written == 1
    assert result.rejected_rows_written == 1

    assert result.affected_event_dates == ("2026-08-17",)

    assert result.affected_rejection_dates == ("2026-08-17",)

    telemetry = DeltaTable(str(silver_dir / TELEMETRY_TABLE_NAME)).to_pandas()

    identity = DeltaTable(str(silver_dir / DEVICE_IDENTITY_TABLE_NAME)).to_pandas()

    rejected = DeltaTable(str(silver_dir / REJECTED_LOGS_TABLE_NAME)).to_pandas()

    assert len(telemetry) == 1
    assert len(identity) == 1
    assert len(rejected) == 1


def test_unknown_batch_returns_noop(
    tmp_path: Path,
) -> None:
    bronze_dir = tmp_path / "01_bronze"

    silver_dir = tmp_path / "02_silver"

    write_bronze_rows(
        bronze_dir,
        [
            build_bronze_row(
                row_id="row-1",
                batch_id="batch-001",
                event_date="2026-08-17",
            )
        ],
    )

    # Primeiro cria a Silver.
    load_silver_data(
        bronze_dir=bronze_dir,
        silver_dir=silver_dir,
    )

    result = load_silver_data(
        bronze_dir=bronze_dir,
        silver_dir=silver_dir,
        batch_ids=("batch-does-not-exist",),
    )

    assert result.mode == "NOOP"
    assert not result.has_changes

    assert result.telemetry_rows_written == 0

    assert result.identity_rows_written == 0

    assert result.rejected_rows_written == 0


def test_late_arriving_batch_rebuilds_only_affected_date(
    tmp_path: Path,
) -> None:
    bronze_dir = tmp_path / "01_bronze"

    silver_dir = tmp_path / "02_silver"

    write_bronze_rows(
        bronze_dir,
        [
            build_bronze_row(
                row_id="old-17",
                batch_id="batch-old",
                event_date="2026-08-17",
            ),
            build_bronze_row(
                row_id="row-18",
                batch_id="batch-other",
                event_date="2026-08-18",
            ),
        ],
    )

    load_silver_data(
        bronze_dir=bronze_dir,
        silver_dir=silver_dir,
    )

    # Late-arriving data para 17/08.
    write_bronze_rows(
        bronze_dir,
        [
            build_bronze_row(
                row_id="late-17",
                batch_id="batch-new",
                event_date="2026-08-17",
            )
        ],
        mode="append",
    )

    result = load_silver_data(
        bronze_dir=bronze_dir,
        silver_dir=silver_dir,
        batch_ids=("batch-new",),
    )

    assert result.mode == "INCREMENTAL"

    assert result.affected_event_dates == ("2026-08-17",)

    telemetry = DeltaTable(str(silver_dir / TELEMETRY_TABLE_NAME)).to_pandas()

    day_17 = telemetry.loc[telemetry["event_date"] == "2026-08-17"]

    day_18 = telemetry.loc[telemetry["event_date"] == "2026-08-18"]

    assert set(day_17["row_id"]) == {
        "old-17",
        "late-17",
    }

    assert set(day_18["row_id"]) == {
        "row-18",
    }


def test_first_incremental_request_falls_back_to_full(
    tmp_path: Path,
) -> None:
    bronze_dir = tmp_path / "01_bronze"
    silver_dir = tmp_path / "02_silver"

    write_bronze_rows(
        bronze_dir,
        [
            build_bronze_row(
                row_id="row-17",
                batch_id="batch-001",
                event_date="2026-08-17",
            ),
            build_bronze_row(
                row_id="row-18",
                batch_id="batch-002",
                event_date="2026-08-18",
            ),
        ],
    )

    result = load_silver_data(
        bronze_dir=bronze_dir,
        silver_dir=silver_dir,
        batch_ids=("batch-002",),
    )

    assert result.mode == "FULL"

    assert result.batch_ids == ("batch-002",)

    assert result.affected_event_dates == (
        "2026-08-17",
        "2026-08-18",
    )

    telemetry = DeltaTable(str(silver_dir / TELEMETRY_TABLE_NAME)).to_pandas()

    assert set(telemetry["row_id"]) == {
        "row-17",
        "row-18",
    }


def test_incremental_unknown_rebuilds_all_unknown_rows(
    tmp_path: Path,
) -> None:
    bronze_dir = tmp_path / "01_bronze"
    silver_dir = tmp_path / "02_silver"

    valid_row = build_bronze_row(
        row_id="valid-row",
        batch_id="batch-valid",
        event_date="2026-08-17",
    )

    old_unknown = build_bronze_row(
        row_id="old-unknown",
        batch_id="batch-old",
        event_date="2026-08-17",
    )

    old_unknown["TM_STAMP"] = "invalid"
    old_unknown["DATA_SERVIDOR"] = "invalid"

    write_bronze_rows(
        bronze_dir,
        [
            valid_row,
            old_unknown,
        ],
    )

    # Cria inicialmente as três tabelas Silver.
    load_silver_data(
        bronze_dir=bronze_dir,
        silver_dir=silver_dir,
    )

    new_unknown = build_bronze_row(
        row_id="new-unknown",
        batch_id="batch-new",
        event_date="2026-08-18",
    )

    new_unknown["TM_STAMP"] = "invalid"
    new_unknown["DATA_SERVIDOR"] = "invalid"

    write_bronze_rows(
        bronze_dir,
        [
            new_unknown,
        ],
        mode="append",
    )

    result = load_silver_data(
        bronze_dir=bronze_dir,
        silver_dir=silver_dir,
        batch_ids=("batch-new",),
    )

    assert result.mode == "INCREMENTAL"

    assert result.affected_event_dates == ()

    assert result.affected_rejection_dates == ("unknown",)

    rejected = DeltaTable(str(silver_dir / REJECTED_LOGS_TABLE_NAME)).to_pandas()

    unknown = rejected.loc[rejected["rejection_date"] == "unknown"]

    assert set(unknown["row_id"]) == {
        "old-unknown",
        "new-unknown",
    }


def test_silver_can_run_from_settings(
    tmp_path: Path,
    monkeypatch,
) -> None:
    data_dir = tmp_path / "data"

    monkeypatch.setenv(
        "QUEO_DATA_DIR",
        str(data_dir),
    )

    settings = load_settings()

    write_bronze_rows(
        settings.bronze_dir,
        [
            build_bronze_row(
                row_id="row-settings",
                batch_id="batch-settings",
                event_date="2026-08-17",
            )
        ],
    )

    result = load_silver(settings)

    assert result.mode == "FULL"

    telemetry_path = settings.silver_dir / TELEMETRY_TABLE_NAME

    assert DeltaTable.is_deltatable(str(telemetry_path))

    telemetry = DeltaTable(str(telemetry_path)).to_pandas()

    assert set(telemetry["row_id"]) == {
        "row-settings",
    }


def test_empty_batch_ids_return_noop_when_silver_exists(
    tmp_path: Path,
) -> None:
    bronze_dir = tmp_path / "01_bronze"

    silver_dir = tmp_path / "02_silver"

    write_bronze_rows(
        bronze_dir,
        [
            build_bronze_row(
                row_id="row-1",
                batch_id="batch-001",
                event_date="2026-08-17",
            )
        ],
    )

    first_result = load_silver_data(
        bronze_dir=bronze_dir,
        silver_dir=silver_dir,
    )

    assert first_result.mode == "FULL"

    result = load_silver_data(
        bronze_dir=bronze_dir,
        silver_dir=silver_dir,
        batch_ids=(),
    )

    assert result.mode == "NOOP"
    assert not result.has_changes

    assert result.batch_ids == ()

    assert result.affected_event_dates == ()

    assert result.affected_rejection_dates == ()

    assert result.telemetry_rows_written == 0

    assert result.identity_rows_written == 0

    assert result.rejected_rows_written == 0
