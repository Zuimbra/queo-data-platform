from datetime import UTC, datetime

import pandas as pd
import pytest

from queo_data_platform.silver.classification import (
    classify_normalized_dataframe,
    validate_normalized_input,
)


def build_normalized_dataframe(
    **overrides: object,
) -> pd.DataFrame:
    data: dict[str, list[object]] = {
        "server_timestamp": [pd.Timestamp("2026-08-17 12:00:00")],
        "device_timestamp": [pd.Timestamp("2026-08-17 11:59:50")],
        "message_type": ["T2"],
        "device_serial_raw": ["M123456789"],
        "device_serial": ["123456789"],
        "device_resolution_method": ["DIRECT"],
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
        "ingestion_date": [pd.Timestamp("2026-08-17").date()],
    }

    for column, value in overrides.items():
        data[column] = [value]

    return pd.DataFrame(data)


def test_missing_required_column_is_rejected() -> None:
    dataframe = build_normalized_dataframe()

    dataframe = dataframe.drop(columns=["message_type"])

    with pytest.raises(
        ValueError,
        match="message_type",
    ):
        validate_normalized_input(dataframe)


def test_t2_is_classified_as_telemetry() -> None:
    dataframe = build_normalized_dataframe(
        message_type="T2",
    )

    result = classify_normalized_dataframe(dataframe)

    assert len(result.telemetry) == 1
    assert result.identity.empty
    assert result.rejected.empty

    assert (
        result.telemetry.loc[
            0,
            "event_date",
        ]
        == "2026-08-17"
    )


def test_t1_is_classified_as_identity() -> None:
    dataframe = build_normalized_dataframe(
        message_type="T1",
    )

    result = classify_normalized_dataframe(dataframe)

    assert result.telemetry.empty
    assert len(result.identity) == 1
    assert result.rejected.empty

    assert (
        result.identity.loc[
            0,
            "event_date",
        ]
        == "2026-08-17"
    )


def test_missing_message_type_is_rejected() -> None:
    dataframe = build_normalized_dataframe(
        message_type=None,
    )

    result = classify_normalized_dataframe(dataframe)

    assert result.telemetry.empty
    assert result.identity.empty

    assert (
        result.rejected.loc[
            0,
            "rejection_reason",
        ]
        == "MISSING_MESSAGE_TYPE"
    )


def test_invalid_message_type_is_rejected() -> None:
    dataframe = build_normalized_dataframe(
        message_type="INVALID",
    )

    result = classify_normalized_dataframe(dataframe)

    assert (
        result.rejected.loc[
            0,
            "rejection_reason",
        ]
        == "INVALID_MESSAGE_TYPE"
    )


def test_missing_timestamps_is_rejected_as_unknown_date() -> None:
    dataframe = build_normalized_dataframe(
        server_timestamp=None,
        device_timestamp=None,
    )

    result = classify_normalized_dataframe(dataframe)

    assert (
        result.rejected.loc[
            0,
            "rejection_reason",
        ]
        == "MISSING_OR_INVALID_TIMESTAMP"
    )

    assert (
        result.rejected.loc[
            0,
            "rejection_date",
        ]
        == "unknown"
    )


def test_missing_device_serial_is_rejected() -> None:
    dataframe = build_normalized_dataframe(
        device_serial_raw=None,
        device_serial=None,
        device_resolution_method="UNRESOLVED",
    )

    result = classify_normalized_dataframe(dataframe)

    assert (
        result.rejected.loc[
            0,
            "rejection_reason",
        ]
        == "MISSING_DEVICE_SERIAL"
    )


def test_resolved_legacy_serial_is_not_rejected() -> None:
    dataframe = build_normalized_dataframe(
        device_serial_raw=None,
        device_serial="202527000021P",
        device_resolution_method=("LEGACY_IMEI"),
    )

    result = classify_normalized_dataframe(dataframe)

    assert len(result.telemetry) == 1

    assert result.rejected.empty


def test_device_timestamp_has_priority() -> None:
    dataframe = build_normalized_dataframe(
        device_timestamp=pd.Timestamp("2026-08-16 23:59:50"),
        server_timestamp=pd.Timestamp("2026-08-17 00:00:10"),
    )

    result = classify_normalized_dataframe(dataframe)

    assert result.telemetry.loc[
        0,
        "event_timestamp",
    ] == pd.Timestamp("2026-08-16 23:59:50")

    assert (
        result.telemetry.loc[
            0,
            "event_date",
        ]
        == "2026-08-16"
    )


def test_server_timestamp_is_used_as_fallback() -> None:
    dataframe = build_normalized_dataframe(
        device_timestamp=None,
        server_timestamp=pd.Timestamp("2026-08-17 12:00:00"),
    )

    result = classify_normalized_dataframe(dataframe)

    assert result.telemetry.loc[
        0,
        "event_timestamp",
    ] == pd.Timestamp("2026-08-17 12:00:00")
