from datetime import UTC, datetime

import pandas as pd

from queo_data_platform.silver.transformation import (
    transform_identity_dataframe,
    transform_telemetry_dataframe,
)


def build_classified_row(
    **overrides: object,
) -> pd.DataFrame:
    data: dict[str, list[object]] = {
        "event_date": ["2026-08-17"],
        "server_timestamp": [pd.Timestamp("2026-08-17 12:00:00")],
        "device_timestamp": [pd.Timestamp("2026-08-17 11:59:50")],
        "event_timestamp": [pd.Timestamp("2026-08-17 11:59:50")],
        "log_type": ["tracker"],
        "message_type": ["T2"],
        "report_type_raw": ["1"],
        "protocol_version": ["1"],
        "device_serial_raw": ["M123456789"],
        "device_serial": ["123456789"],
        "device_resolution_method": ["DIRECT"],
        "terminal_status": ["OK"],
        "battery_voltage_raw": ["12.5"],
        "location_status_raw": ["A"],
        "latitude_raw": ["-3.7319"],
        "longitude_raw": ["-38.5267"],
        "speed_raw": ["45.5"],
        "direction_raw": ["180"],
        "internal_battery_raw": ["4.1"],
        "odometer_trip_raw": ["100.5"],
        "odometer_total_raw": ["20000"],
        "horimeter_raw": ["1500"],
        "hdop_raw": ["1.2"],
        "mcc": ["724"],
        "mnc": ["05"],
        "lac": ["100"],
        "cell_id": ["200"],
        "rx_level_raw": ["-70"],
        "serial_count_raw": ["15"],
        "transmission_technology": ["GPRS"],
        "message_group": ["G1"],
        "io_status": ["0"],
        "driver_id": ["driver"],
        "passenger_id": ["passenger"],
        "rpm_raw": ["2500"],
        "tachograph_speed_raw": ["45"],
        "tachograph_odometer_raw": ["20000"],
        "temperature_1_raw": ["25"],
        "temperature_2_raw": ["26"],
        "temperature_3_raw": ["27"],
        "temperature_4_raw": ["28"],
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


def test_telemetry_numeric_fields_are_typed() -> None:
    result = transform_telemetry_dataframe(build_classified_row())

    assert result.loc[0, "latitude"] == -3.7319
    assert result.loc[0, "longitude"] == -38.5267
    assert result.loc[0, "speed"] == 45.5
    assert result.loc[0, "rpm"] == 2500.0
    assert result.loc[0, "serial_count"] == 15


def test_invalid_numeric_value_becomes_null() -> None:
    result = transform_telemetry_dataframe(
        build_classified_row(
            speed_raw="invalid",
        )
    )

    assert pd.isna(
        result.loc[
            0,
            "speed",
        ]
    )


def test_resolved_device_serial_is_preserved() -> None:
    result = transform_telemetry_dataframe(
        build_classified_row(
            device_serial_raw="M123456789",
            device_serial="123456789",
            device_resolution_method="DIRECT",
        )
    )

    assert (
        result.loc[
            0,
            "device_serial",
        ]
        == "123456789"
    )

    assert (
        result.loc[
            0,
            "device_resolution_method",
        ]
        == "DIRECT"
    )


def test_valid_coordinates_are_identified() -> None:
    result = transform_telemetry_dataframe(build_classified_row())

    assert bool(
        result.loc[
            0,
            "has_valid_coordinates",
        ]
    )

    assert (
        result.loc[
            0,
            "position_quality",
        ]
        == "VALID"
    )


def test_missing_coordinates_are_identified() -> None:
    result = transform_telemetry_dataframe(
        build_classified_row(
            latitude_raw=None,
        )
    )

    assert not bool(
        result.loc[
            0,
            "has_valid_coordinates",
        ]
    )

    assert (
        result.loc[
            0,
            "position_quality",
        ]
        == "MISSING_COORDINATES"
    )


def test_invalid_coordinates_are_identified() -> None:
    result = transform_telemetry_dataframe(
        build_classified_row(
            latitude_raw="120",
        )
    )

    assert not bool(
        result.loc[
            0,
            "has_valid_coordinates",
        ]
    )

    assert (
        result.loc[
            0,
            "position_quality",
        ]
        == "INVALID_COORDINATES"
    )


def test_high_hdop_marks_low_precision() -> None:
    result = transform_telemetry_dataframe(
        build_classified_row(
            hdop_raw="8.5",
        )
    )

    assert bool(
        result.loc[
            0,
            "has_valid_coordinates",
        ]
    )

    assert (
        result.loc[
            0,
            "position_quality",
        ]
        == "LOW_GPS_PRECISION"
    )


def test_identity_fields_are_extracted_from_t1_positions() -> None:
    dataframe = build_classified_row(
        message_type="T1",
        battery_voltage_raw="8955000000000000001",
        location_status_raw="aux",
        latitude_raw="724000000000001",
        longitude_raw="359000000000001",
    )

    result = transform_identity_dataframe(dataframe)

    assert (
        result.loc[
            0,
            "iccid",
        ]
        == "8955000000000000001"
    )

    assert (
        result.loc[
            0,
            "imsi",
        ]
        == "724000000000001"
    )

    assert (
        result.loc[
            0,
            "imei",
        ]
        == "359000000000001"
    )


def test_valid_identity_formats_are_detected() -> None:
    dataframe = build_classified_row(
        message_type="T1",
        battery_voltage_raw="8955000000000000001",
        latitude_raw="724000000000001",
        longitude_raw="359000000000001",
    )

    result = transform_identity_dataframe(dataframe)

    assert bool(
        result.loc[
            0,
            "has_valid_iccid_format",
        ]
    )

    assert bool(
        result.loc[
            0,
            "has_valid_imsi_format",
        ]
    )

    assert bool(
        result.loc[
            0,
            "has_valid_imei_format",
        ]
    )


def test_invalid_identity_formats_are_detected() -> None:
    dataframe = build_classified_row(
        message_type="T1",
        battery_voltage_raw="123",
        latitude_raw="abc",
        longitude_raw="123",
    )

    result = transform_identity_dataframe(dataframe)

    assert not bool(
        result.loc[
            0,
            "has_valid_iccid_format",
        ]
    )

    assert not bool(
        result.loc[
            0,
            "has_valid_imsi_format",
        ]
    )

    assert not bool(
        result.loc[
            0,
            "has_valid_imei_format",
        ]
    )


def test_lineage_is_preserved_in_telemetry() -> None:
    result = transform_telemetry_dataframe(build_classified_row())

    assert (
        result.loc[
            0,
            "row_id",
        ]
        == "row-001"
    )

    assert (
        result.loc[
            0,
            "batch_id",
        ]
        == "batch-001"
    )

    assert (
        result.loc[
            0,
            "source_file",
        ]
        == "tracker.csv"
    )
