from pathlib import Path

import pandas as pd
from deltalake import DeltaTable

from queo_data_platform.config.settings import (
    Settings,
)
from queo_data_platform.contracts.gold import (
    DATA_QUALITY_SUMMARY_TABLE_NAME,
    DEVICE_DAILY_SUMMARY_TABLE_NAME,
    DEVICE_LAST_POSITION_TABLE_NAME,
    DEVICE_ROUTE_POINTS_TABLE_NAME,
    DIM_DEVICE_TABLE_NAME,
)
from queo_data_platform.contracts.tracker import (
    RAW_TRACKER_REQUIRED_COLUMNS,
)
from queo_data_platform.pipeline.service import (
    run_pipeline,
)


def build_test_settings(
    tmp_path: Path,
) -> Settings:
    data_dir = tmp_path / "data"

    raw_dir = data_dir / "raw"

    lakehouse_dir = data_dir / "lakehouse"

    return Settings(
        project_root=tmp_path,
        data_dir=data_dir,
        raw_dir=raw_dir,
        inbox_dir=(raw_dir / "inbox"),
        archive_dir=(raw_dir / "archive"),
        quarantine_dir=(raw_dir / "quarantine"),
        lakehouse_dir=lakehouse_dir,
        control_dir=(lakehouse_dir / "00_control"),
        bronze_dir=(lakehouse_dir / "01_bronze"),
        silver_dir=(lakehouse_dir / "02_silver"),
        gold_dir=(lakehouse_dir / "03_gold"),
    )


def build_tracker_row(
    *,
    event_date: str,
    event_time: str,
    message_type: str,
    serial_count: int,
) -> dict[str, object]:
    row: dict[str, object] = {
        column: "value" for column in (RAW_TRACKER_REQUIRED_COLUMNS)
    }

    row.update(
        {
            "DATA_SERVIDOR": (f"{event_date} {event_time}"),
            "TM_STAMP": (f"{event_date} {event_time}"),
            "TIPO_LOG": "tracker",
            "MESS_TYPE": message_type,
            "REPT_TYPE": "1",
            "PRT_VER": "1",
            "S/N ou IMEI": "M123456789",
            "TERM_STATUS": "OK",
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
            "MCC": "724",
            "MNC": "05",
            "LAC": "100",
            "CELL_ID": "200",
            "RX_LEVEL": "-70",
            "SER_COUNT": str(serial_count),
            "TX_TECH": "GPRS",
            "GRP_MSG": "G1",
            "IO_STATUS": "0",
            "DRIVER_ID": "",
            "PASS_ID": "",
            "RPM": "2500",
            "TACHO_SPD": "45",
            "TACHO_ODO": "20000",
            "TEMP_1": "25",
            "TEMP_2": "26",
            "TEMP_3": "27",
            "TEMP_4": "28",
        }
    )

    return row


def build_identity_tracker_row(
    *,
    event_date: str,
    serial_count: int,
) -> dict[str, object]:
    row = build_tracker_row(
        event_date=event_date,
        event_time="09:00:00",
        message_type="T1",
        serial_count=serial_count,
    )

    # T1 reutiliza esses campos para
    # identificadores do equipamento.
    row["BAT_VOLT"] = "8955000000000000001"

    row["LOC_STATUS"] = "aux"

    row["LAT"] = "724000000000001"

    row["LONT"] = "359000000000001"

    return row


def create_tracker_file(
    file_path: Path,
    *,
    event_date: str,
) -> None:
    file_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    rows = [
        build_tracker_row(
            event_date=event_date,
            event_time="10:00:00",
            message_type="T2",
            serial_count=1,
        ),
        build_identity_tracker_row(
            event_date=event_date,
            serial_count=2,
        ),
        build_tracker_row(
            event_date=event_date,
            event_time="11:00:00",
            message_type="INVALID",
            serial_count=3,
        ),
    ]

    pd.DataFrame(rows).to_csv(
        file_path,
        index=False,
    )


def test_pipeline_processes_all_layers(
    tmp_path: Path,
) -> None:
    settings = build_test_settings(tmp_path)

    source_file = settings.inbox_dir / "tracker-17.csv"

    create_tracker_file(
        source_file,
        event_date="2026-08-17",
    )

    result = run_pipeline(settings)

    assert result.bronze.has_new_data

    assert result.bronze.inserted_row_count == 3

    assert len(result.bronze.batch_ids) == 1

    # Na primeira execução a Silver ainda
    # não existe, portanto faz fallback FULL.
    assert result.silver.mode == "FULL"

    assert result.silver.telemetry_rows_written == 1

    assert result.silver.identity_rows_written == 1

    assert result.silver.rejected_rows_written == 1

    assert result.gold.mode == "FULL"

    assert result.has_new_data
    assert result.has_changes

    assert not source_file.exists()

    assert (settings.archive_dir / "tracker-17.csv").exists()

    for table_name in (
        DIM_DEVICE_TABLE_NAME,
        DEVICE_LAST_POSITION_TABLE_NAME,
        DEVICE_ROUTE_POINTS_TABLE_NAME,
        DEVICE_DAILY_SUMMARY_TABLE_NAME,
        DATA_QUALITY_SUMMARY_TABLE_NAME,
    ):
        assert DeltaTable.is_deltatable(str(settings.gold_dir / table_name))


def test_pipeline_returns_noop_without_new_files(
    tmp_path: Path,
) -> None:
    settings = build_test_settings(tmp_path)

    create_tracker_file(
        settings.inbox_dir / "tracker-17.csv",
        event_date="2026-08-17",
    )

    first_result = run_pipeline(settings)

    assert first_result.has_changes

    second_result = run_pipeline(settings)

    assert second_result.bronze.discovered_file_count == 0

    assert second_result.bronze.batch_ids == ()

    assert second_result.silver.mode == "NOOP"

    assert second_result.gold.mode == "NOOP"

    assert not second_result.has_new_data
    assert not second_result.has_changes


def test_pipeline_propagates_new_batch_incrementally(
    tmp_path: Path,
) -> None:
    settings = build_test_settings(tmp_path)

    create_tracker_file(
        settings.inbox_dir / "tracker-17.csv",
        event_date="2026-08-17",
    )

    first_result = run_pipeline(settings)

    assert first_result.silver.mode == "FULL"

    assert first_result.gold.mode == "FULL"

    create_tracker_file(
        settings.inbox_dir / "tracker-18.csv",
        event_date="2026-08-18",
    )

    result = run_pipeline(settings)

    assert result.bronze.has_new_data

    assert len(result.bronze.batch_ids) == 1

    assert result.silver.mode == "INCREMENTAL"

    assert result.silver.affected_event_dates == ("2026-08-18",)

    assert result.gold.mode == "INCREMENTAL"

    assert result.gold.affected_event_dates == ("2026-08-18",)

    routes = DeltaTable(
        str(settings.gold_dir / DEVICE_ROUTE_POINTS_TABLE_NAME)
    ).to_pandas()

    assert set(routes["event_date"]) == {
        "2026-08-17",
        "2026-08-18",
    }
