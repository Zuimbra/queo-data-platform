import duckdb
import pandas as pd

from queo_data_platform.gold.base import (
    SILVER_IDENTITY_RELATION,
    SILVER_TELEMETRY_RELATION,
)
from queo_data_platform.gold.incremental import (
    GoldIncrementalScope,
    build_gold_incremental_scope,
    build_quality_dates,
    discover_affected_devices,
    normalize_partition_values,
)


def register_incremental_sources(
    connection: duckdb.DuckDBPyConnection,
) -> None:
    telemetry = pd.DataFrame(
        {
            "event_date": [
                "2026-08-17",
                "2026-08-18",
                "2026-08-18",
            ],
            "device_serial": [
                "1001",
                "2002",
                "3003",
            ],
        }
    )

    identity = pd.DataFrame(
        {
            "event_date": [
                "2026-08-17",
                "2026-08-19",
            ],
            "device_serial": [
                "4004",
                "5005",
            ],
        }
    )

    connection.register(
        SILVER_TELEMETRY_RELATION,
        telemetry,
    )

    connection.register(
        SILVER_IDENTITY_RELATION,
        identity,
    )


def test_normalize_partition_values() -> None:
    result = normalize_partition_values(
        [
            "2026-08-18",
            " 2026-08-17 ",
            "2026-08-18",
            "",
        ]
    )

    assert result == (
        "2026-08-17",
        "2026-08-18",
    )


def test_quality_dates_combine_event_and_rejection_dates() -> None:
    result = build_quality_dates(
        (
            "2026-08-17",
            "2026-08-18",
        ),
        (
            "2026-08-18",
            "unknown",
        ),
    )

    assert result == (
        "2026-08-17",
        "2026-08-18",
        "unknown",
    )


def test_affected_devices_include_telemetry_and_identity() -> None:
    connection = duckdb.connect()

    try:
        register_incremental_sources(connection)

        result = discover_affected_devices(
            connection,
            ("2026-08-17",),
        )

        assert result == (
            "1001",
            "4004",
        )

    finally:
        connection.close()


def test_affected_devices_ignore_other_dates() -> None:
    connection = duckdb.connect()

    try:
        register_incremental_sources(connection)

        result = discover_affected_devices(
            connection,
            ("2026-08-18",),
        )

        assert result == (
            "2002",
            "3003",
        )

        assert "5005" not in result

    finally:
        connection.close()


def test_unknown_rejection_does_not_affect_entities() -> None:
    connection = duckdb.connect()

    try:
        register_incremental_sources(connection)

        scope = build_gold_incremental_scope(
            connection,
            affected_event_dates=(),
            affected_rejection_dates=("unknown",),
        )

        assert scope.event_dates == ()

        assert scope.rejection_dates == ("unknown",)

        assert scope.quality_dates == ("unknown",)

        assert scope.affected_devices == ()

        assert not scope.has_entity_changes

    finally:
        connection.close()


def test_gold_incremental_scope_combines_all_changes() -> None:
    connection = duckdb.connect()

    try:
        register_incremental_sources(connection)

        scope = build_gold_incremental_scope(
            connection,
            affected_event_dates=(
                "2026-08-17",
                "2026-08-18",
            ),
            affected_rejection_dates=(
                "2026-08-18",
                "unknown",
            ),
        )

        assert scope == GoldIncrementalScope(
            event_dates=(
                "2026-08-17",
                "2026-08-18",
            ),
            rejection_dates=(
                "2026-08-18",
                "unknown",
            ),
            quality_dates=(
                "2026-08-17",
                "2026-08-18",
                "unknown",
            ),
            affected_devices=(
                "1001",
                "2002",
                "3003",
                "4004",
            ),
        )

        assert not scope.is_empty
        assert scope.has_entity_changes

    finally:
        connection.close()
