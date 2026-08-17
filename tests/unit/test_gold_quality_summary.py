import duckdb
import pandas as pd

from queo_data_platform.gold.base import (
    SILVER_IDENTITY_RELATION,
    SILVER_REJECTED_RELATION,
    SILVER_TELEMETRY_RELATION,
)
from queo_data_platform.gold.quality_summary import (
    build_data_quality_summary,
)


def build_event_dataframe(
    dates: list[str],
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_date": dates,
        }
    )


def build_rejected_dataframe(
    rows: list[tuple[str | None, str]],
) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "rejection_date": [date for date, _ in rows],
            "rejection_reason": [reason for _, reason in rows],
        }
    )


def empty_event_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "event_date": pd.Series(dtype="string"),
        }
    )


def empty_rejected_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "rejection_date": pd.Series(dtype="string"),
            "rejection_reason": pd.Series(dtype="string"),
        }
    )


def register_quality_sources(
    connection: duckdb.DuckDBPyConnection,
    *,
    telemetry: pd.DataFrame,
    identity: pd.DataFrame,
    rejected: pd.DataFrame,
) -> None:
    connection.register(
        SILVER_TELEMETRY_RELATION,
        telemetry,
    )

    connection.register(
        SILVER_IDENTITY_RELATION,
        identity,
    )

    connection.register(
        SILVER_REJECTED_RELATION,
        rejected,
    )


def test_quality_summary_combines_accepted_and_rejected_events() -> None:
    connection = duckdb.connect()

    try:
        register_quality_sources(
            connection,
            telemetry=build_event_dataframe(
                [
                    "2026-08-17",
                    "2026-08-17",
                    "2026-08-17",
                ]
            ),
            identity=build_event_dataframe(
                [
                    "2026-08-17",
                ]
            ),
            rejected=build_rejected_dataframe(
                [
                    (
                        "2026-08-17",
                        "INVALID_MESSAGE_TYPE",
                    ),
                ]
            ),
        )

        result = build_data_quality_summary(connection).to_pandas()

        assert len(result) == 1

        row = result.iloc[0]

        assert row["metric_date"] == "2026-08-17"

        assert row["telemetry_event_count"] == 3
        assert row["identity_event_count"] == 1

        assert row["accepted_event_count"] == 4

        assert row["rejected_event_count"] == 1

        assert row["total_event_count"] == 5

        assert row["rejection_percentage"] == 20.0

    finally:
        connection.close()


def test_quality_summary_counts_rejection_reasons() -> None:
    connection = duckdb.connect()

    try:
        register_quality_sources(
            connection,
            telemetry=empty_event_dataframe(),
            identity=empty_event_dataframe(),
            rejected=build_rejected_dataframe(
                [
                    (
                        "2026-08-17",
                        "MISSING_MESSAGE_TYPE",
                    ),
                    (
                        "2026-08-17",
                        "MISSING_MESSAGE_TYPE",
                    ),
                    (
                        "2026-08-17",
                        "INVALID_MESSAGE_TYPE",
                    ),
                    (
                        "2026-08-17",
                        "MISSING_OR_INVALID_TIMESTAMP",
                    ),
                    (
                        "2026-08-17",
                        "MISSING_DEVICE_SERIAL",
                    ),
                    (
                        "2026-08-17",
                        "UNKNOWN_REJECTION_REASON",
                    ),
                ]
            ),
        )

        result = build_data_quality_summary(connection).to_pandas()

        row = result.iloc[0]

        assert row["rejected_event_count"] == 6

        assert row["missing_message_type_count"] == 2

        assert row["invalid_message_type_count"] == 1

        assert row["invalid_timestamp_count"] == 1

        assert row["missing_device_serial_count"] == 1

        assert row["unknown_rejection_count"] == 1

    finally:
        connection.close()


def test_quality_summary_preserves_dates_from_all_sources() -> None:
    connection = duckdb.connect()

    try:
        register_quality_sources(
            connection,
            telemetry=build_event_dataframe(
                [
                    "2026-08-17",
                ]
            ),
            identity=build_event_dataframe(
                [
                    "2026-08-18",
                ]
            ),
            rejected=build_rejected_dataframe(
                [
                    (
                        "2026-08-19",
                        "INVALID_MESSAGE_TYPE",
                    ),
                ]
            ),
        )

        result = build_data_quality_summary(connection).to_pandas()

        assert result["metric_date"].tolist() == [
            "2026-08-17",
            "2026-08-18",
            "2026-08-19",
        ]

        day_17 = result.loc[result["metric_date"] == "2026-08-17"].iloc[0]

        assert day_17["telemetry_event_count"] == 1

        assert day_17["identity_event_count"] == 0

        assert day_17["rejected_event_count"] == 0

    finally:
        connection.close()


def test_quality_summary_supports_unknown_rejection_date() -> None:
    connection = duckdb.connect()

    try:
        register_quality_sources(
            connection,
            telemetry=empty_event_dataframe(),
            identity=empty_event_dataframe(),
            rejected=build_rejected_dataframe(
                [
                    (
                        None,
                        "MISSING_OR_INVALID_TIMESTAMP",
                    ),
                    (
                        "unknown",
                        "MISSING_OR_INVALID_TIMESTAMP",
                    ),
                ]
            ),
        )

        result = build_data_quality_summary(connection).to_pandas()

        assert len(result) == 1

        row = result.iloc[0]

        assert row["metric_date"] == "unknown"

        assert row["rejected_event_count"] == 2

        assert row["invalid_timestamp_count"] == 2

        assert row["total_event_count"] == 2
        assert row["rejection_percentage"] == 100.0

    finally:
        connection.close()


def test_quality_summary_can_filter_metric_dates() -> None:
    connection = duckdb.connect()

    try:
        register_quality_sources(
            connection,
            telemetry=build_event_dataframe(
                [
                    "2026-08-17",
                    "2026-08-18",
                    "2026-08-19",
                ]
            ),
            identity=empty_event_dataframe(),
            rejected=empty_rejected_dataframe(),
        )

        result = build_data_quality_summary(
            connection,
            metric_dates=("2026-08-18",),
        ).to_pandas()

        assert len(result) == 1

        assert result["metric_date"].tolist() == ["2026-08-18"]

    finally:
        connection.close()


def test_quality_summary_counts_all_silver_events() -> None:
    connection = duckdb.connect()

    try:
        register_quality_sources(
            connection,
            telemetry=build_event_dataframe(
                [
                    "2026-08-17",
                    "2026-08-17",
                ]
            ),
            identity=empty_event_dataframe(),
            rejected=empty_rejected_dataframe(),
        )

        result = build_data_quality_summary(connection).to_pandas()

        row = result.iloc[0]

        assert row["telemetry_event_count"] == 2

        assert row["accepted_event_count"] == 2

    finally:
        connection.close()
