import pandas as pd
import pytest

from queo_data_platform.silver.identity_resolution import (
    build_unambiguous_imei_to_serial_map,
    build_unambiguous_imei_to_serial_map_from_identity_events,
    build_unambiguous_legacy_file_imei_map,
    merge_unambiguous_imei_to_serial_maps,
    normalize_device_serial,
    resolve_identity_dataframe,
    validate_identity_resolution_input,
)

KNOWN_IMEI = "354173560222769"

KNOWN_DEVICE_SERIAL_RAW = "M202527000021P"

KNOWN_DEVICE_SERIAL = "202527000021P"


def build_normalized_row(
    **overrides: object,
) -> dict[str, object]:
    row: dict[str, object] = {
        "server_timestamp": pd.Timestamp("2026-06-01 12:00:00"),
        "device_timestamp": pd.Timestamp("2026-06-01 11:59:50"),
        "message_type": "T2",
        "protocol_version": "V14.06.111",
        "device_serial_raw": None,
        "longitude_raw": None,
        "source_file": ("logs_rastreador_2026-06-01.csv"),
    }

    row.update(overrides)

    return row


def test_missing_required_column_is_rejected() -> None:
    dataframe = pd.DataFrame([build_normalized_row()]).drop(
        columns=["protocol_version"]
    )

    with pytest.raises(
        ValueError,
        match="protocol_version",
    ):
        validate_identity_resolution_input(dataframe)


def test_direct_serial_is_normalized() -> None:
    result = normalize_device_serial(KNOWN_DEVICE_SERIAL_RAW)

    assert result == KNOWN_DEVICE_SERIAL


def test_serial_without_prefix_is_preserved() -> None:
    result = normalize_device_serial(KNOWN_DEVICE_SERIAL)

    assert result == KNOWN_DEVICE_SERIAL


def test_imei_to_serial_map_keeps_unambiguous_relation() -> None:
    dataframe = pd.DataFrame(
        [
            build_normalized_row(
                message_type="T1",
                device_serial_raw=(KNOWN_DEVICE_SERIAL_RAW),
                longitude_raw=KNOWN_IMEI,
            )
        ]
    )

    result = build_unambiguous_imei_to_serial_map(dataframe)

    assert result == {KNOWN_IMEI: KNOWN_DEVICE_SERIAL}


def test_imei_to_serial_map_discards_ambiguous_relation() -> None:
    dataframe = pd.DataFrame(
        [
            build_normalized_row(
                message_type="T1",
                device_serial_raw="MDEVICE-A",
                longitude_raw=KNOWN_IMEI,
            ),
            build_normalized_row(
                message_type="T1",
                device_serial_raw="MDEVICE-B",
                longitude_raw=KNOWN_IMEI,
            ),
        ]
    )

    result = build_unambiguous_imei_to_serial_map(dataframe)

    assert KNOWN_IMEI not in result


def test_legacy_file_map_accepts_single_distinct_imei() -> None:
    dataframe = pd.DataFrame(
        [
            build_normalized_row(
                message_type="T1",
                longitude_raw=KNOWN_IMEI,
            ),
            build_normalized_row(
                message_type="T1",
                longitude_raw=KNOWN_IMEI,
            ),
        ]
    )

    result = build_unambiguous_legacy_file_imei_map(dataframe)

    assert result == {"logs_rastreador_2026-06-01.csv": KNOWN_IMEI}


def test_legacy_file_map_discards_multiple_imeis() -> None:
    dataframe = pd.DataFrame(
        [
            build_normalized_row(
                message_type="T1",
                longitude_raw=KNOWN_IMEI,
            ),
            build_normalized_row(
                message_type="T1",
                longitude_raw="359000000000001",
            ),
        ]
    )

    result = build_unambiguous_legacy_file_imei_map(dataframe)

    assert result == {}


def test_direct_identity_preserves_raw_value() -> None:
    dataframe = pd.DataFrame(
        [build_normalized_row(device_serial_raw=(KNOWN_DEVICE_SERIAL_RAW))]
    )

    resolved = resolve_identity_dataframe(
        dataframe,
        imei_to_serial={},
    )

    assert (
        resolved.loc[
            0,
            "device_serial_raw",
        ]
        == KNOWN_DEVICE_SERIAL_RAW
    )

    assert (
        resolved.loc[
            0,
            "device_serial",
        ]
        == KNOWN_DEVICE_SERIAL
    )

    assert (
        resolved.loc[
            0,
            "device_resolution_method",
        ]
        == "DIRECT"
    )


def test_legacy_tracker_row_is_resolved_from_file_imei() -> None:
    dataframe = pd.DataFrame(
        [
            build_normalized_row(
                message_type="T1",
                longitude_raw=KNOWN_IMEI,
            ),
            build_normalized_row(
                message_type="T2",
                longitude_raw="-38.5267",
            ),
        ]
    )

    resolved = resolve_identity_dataframe(
        dataframe,
        imei_to_serial={KNOWN_IMEI: KNOWN_DEVICE_SERIAL},
    )

    assert pd.isna(
        resolved.loc[
            1,
            "device_serial_raw",
        ]
    )

    assert (
        resolved.loc[
            1,
            "device_serial",
        ]
        == KNOWN_DEVICE_SERIAL
    )

    assert (
        resolved.loc[
            1,
            "device_resolution_method",
        ]
        == "LEGACY_IMEI"
    )


def test_external_traffic_does_not_inherit_file_identity() -> None:
    dataframe = pd.DataFrame(
        [
            build_normalized_row(
                message_type="T1",
                longitude_raw=KNOWN_IMEI,
            ),
            build_normalized_row(
                message_type="GET / HTTP/1.1",
            ),
        ]
    )

    resolved = resolve_identity_dataframe(
        dataframe,
        imei_to_serial={KNOWN_IMEI: KNOWN_DEVICE_SERIAL},
    )

    assert pd.isna(
        resolved.loc[
            1,
            "device_serial",
        ]
    )

    assert (
        resolved.loc[
            1,
            "device_resolution_method",
        ]
        == "UNRESOLVED"
    )


def test_missing_timestamp_prevents_legacy_resolution() -> None:
    dataframe = pd.DataFrame(
        [
            build_normalized_row(
                message_type="T1",
                longitude_raw=KNOWN_IMEI,
            ),
            build_normalized_row(
                message_type="T2",
                server_timestamp=None,
                device_timestamp=None,
            ),
        ]
    )

    resolved = resolve_identity_dataframe(
        dataframe,
        imei_to_serial={KNOWN_IMEI: KNOWN_DEVICE_SERIAL},
    )

    assert pd.isna(
        resolved.loc[
            1,
            "device_serial",
        ]
    )

    assert (
        resolved.loc[
            1,
            "device_resolution_method",
        ]
        == "UNRESOLVED"
    )


def test_unknown_imei_remains_unresolved() -> None:
    dataframe = pd.DataFrame(
        [
            build_normalized_row(
                message_type="T1",
                longitude_raw=KNOWN_IMEI,
            ),
            build_normalized_row(
                message_type="T2",
            ),
        ]
    )

    resolved = resolve_identity_dataframe(
        dataframe,
        imei_to_serial={},
    )

    assert pd.isna(
        resolved.loc[
            1,
            "device_serial",
        ]
    )

    assert (
        resolved.loc[
            1,
            "device_resolution_method",
        ]
        == "UNRESOLVED"
    )


def test_identity_events_build_historical_reference() -> None:
    dataframe = pd.DataFrame(
        [
            {
                "device_serial_raw": (KNOWN_DEVICE_SERIAL_RAW),
                "imei": KNOWN_IMEI,
            }
        ]
    )

    result = build_unambiguous_imei_to_serial_map_from_identity_events(dataframe)

    assert result == {KNOWN_IMEI: KNOWN_DEVICE_SERIAL}


def test_inferred_identity_is_not_used_as_reference() -> None:
    dataframe = pd.DataFrame(
        [
            {
                "device_serial_raw": None,
                "device_serial": (KNOWN_DEVICE_SERIAL),
                "imei": KNOWN_IMEI,
            }
        ]
    )

    result = build_unambiguous_imei_to_serial_map_from_identity_events(dataframe)

    assert result == {}


def test_historical_reference_discards_ambiguity() -> None:
    dataframe = pd.DataFrame(
        [
            {
                "device_serial_raw": "MDEVICE-A",
                "imei": KNOWN_IMEI,
            },
            {
                "device_serial_raw": "MDEVICE-B",
                "imei": KNOWN_IMEI,
            },
        ]
    )

    result = build_unambiguous_imei_to_serial_map_from_identity_events(dataframe)

    assert result == {}


def test_merge_preserves_same_identity() -> None:
    result = merge_unambiguous_imei_to_serial_maps(
        {
            KNOWN_IMEI: KNOWN_DEVICE_SERIAL,
        },
        {
            KNOWN_IMEI: (KNOWN_DEVICE_SERIAL_RAW),
        },
    )

    assert result == {KNOWN_IMEI: KNOWN_DEVICE_SERIAL}


def test_merge_discards_conflicting_identity() -> None:
    result = merge_unambiguous_imei_to_serial_maps(
        {
            KNOWN_IMEI: KNOWN_DEVICE_SERIAL,
        },
        {
            KNOWN_IMEI: "ANOTHER-DEVICE",
        },
    )

    assert result == {}


def test_legacy_resolution_normalizes_source_file() -> None:
    dataframe = pd.DataFrame(
        [
            build_normalized_row(
                message_type="T1",
                longitude_raw=KNOWN_IMEI,
                source_file="tracker-legacy.csv",
            ),
            build_normalized_row(
                message_type="T2",
                source_file=" tracker-legacy.csv ",
            ),
        ]
    )

    resolved = resolve_identity_dataframe(
        dataframe,
        imei_to_serial={KNOWN_IMEI: KNOWN_DEVICE_SERIAL},
    )

    assert (
        resolved.loc[
            1,
            "device_serial",
        ]
        == KNOWN_DEVICE_SERIAL
    )

    assert (
        resolved.loc[
            1,
            "device_resolution_method",
        ]
        == "LEGACY_IMEI"
    )
