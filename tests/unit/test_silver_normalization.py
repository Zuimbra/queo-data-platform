from datetime import UTC, datetime

import pandas as pd
import pytest

from queo_data_platform.contracts.tracker import (
    RAW_TRACKER_REQUIRED_COLUMNS,
)
from queo_data_platform.silver.normalization import (
    normalize_bronze_dataframe,
    validate_bronze_input_columns,
)


def build_bronze_dataframe(
    **overrides: object,
) -> pd.DataFrame:
    data: dict[str, list[object]] = {
        column: ["value"] for column in RAW_TRACKER_REQUIRED_COLUMNS
    }

    data.update(
        {
            "DATA_SERVIDOR": ["2026-08-17 12:00:00"],
            "TM_STAMP": ["2026-08-17 11:59:50"],
            "source_file": ["tracker.csv"],
            "source_file_hash": ["hash-001"],
            "source_row_number": [1],
            "row_id": ["row-001"],
            "batch_id": ["batch-001"],
            "ingested_at": [
                datetime(
                    2026,
                    8,
                    17,
                    12,
                    1,
                    tzinfo=UTC,
                )
            ],
            "ingestion_date": ["2026-08-17"],
        }
    )

    for column, value in overrides.items():
        data[column] = [value]

    return pd.DataFrame(data)


def test_missing_bronze_column_is_rejected() -> None:
    dataframe = build_bronze_dataframe()

    dataframe = dataframe.drop(columns=["TM_STAMP"])

    with pytest.raises(
        ValueError,
        match="TM_STAMP",
    ):
        validate_bronze_input_columns(dataframe)


def test_text_fields_are_trimmed() -> None:
    dataframe = build_bronze_dataframe(
        TIPO_LOG="  tracker  ",
        MESS_TYPE="  T2  ",
    )

    normalized = normalize_bronze_dataframe(dataframe)

    assert (
        normalized.loc[
            0,
            "log_type",
        ]
        == "tracker"
    )

    assert (
        normalized.loc[
            0,
            "message_type",
        ]
        == "T2"
    )


def test_empty_strings_become_null() -> None:
    dataframe = build_bronze_dataframe(
        DRIVER_ID="   ",
    )

    normalized = normalize_bronze_dataframe(dataframe)

    assert pd.isna(
        normalized.loc[
            0,
            "driver_id",
        ]
    )


def test_valid_timestamps_are_converted() -> None:
    dataframe = build_bronze_dataframe()

    normalized = normalize_bronze_dataframe(dataframe)

    assert normalized.loc[
        0,
        "server_timestamp",
    ] == pd.Timestamp("2026-08-17 12:00:00")

    assert normalized.loc[
        0,
        "device_timestamp",
    ] == pd.Timestamp("2026-08-17 11:59:50")


def test_invalid_timestamp_becomes_null() -> None:
    dataframe = build_bronze_dataframe(
        TM_STAMP="invalid-timestamp",
    )

    normalized = normalize_bronze_dataframe(dataframe)

    assert pd.isna(
        normalized.loc[
            0,
            "device_timestamp",
        ]
    )


def test_protocol_fields_remain_text_before_classification() -> None:
    dataframe = build_bronze_dataframe(
        BAT_VOLT=" 8955000000000000001 ",
        LAT=" 724000000000001 ",
        LONT=" 359000000000001 ",
    )

    normalized = normalize_bronze_dataframe(dataframe)

    assert (
        normalized.loc[
            0,
            "battery_voltage_raw",
        ]
        == "8955000000000000001"
    )

    assert (
        normalized.loc[
            0,
            "latitude_raw",
        ]
        == "724000000000001"
    )

    assert (
        normalized.loc[
            0,
            "longitude_raw",
        ]
        == "359000000000001"
    )


def test_bronze_lineage_is_preserved() -> None:
    dataframe = build_bronze_dataframe()

    normalized = normalize_bronze_dataframe(dataframe)

    assert (
        normalized.loc[
            0,
            "source_file",
        ]
        == "tracker.csv"
    )

    assert (
        normalized.loc[
            0,
            "source_file_hash",
        ]
        == "hash-001"
    )

    assert (
        normalized.loc[
            0,
            "source_row_number",
        ]
        == 1
    )

    assert (
        normalized.loc[
            0,
            "row_id",
        ]
        == "row-001"
    )

    assert (
        normalized.loc[
            0,
            "batch_id",
        ]
        == "batch-001"
    )
