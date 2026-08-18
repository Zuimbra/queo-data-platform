from queo_data_platform.bronze.service import (
    BronzeLoadResult,
)
from queo_data_platform.cli import (
    format_pipeline_result,
)
from queo_data_platform.gold.service import (
    GoldLoadResult,
)
from queo_data_platform.pipeline.service import (
    PipelineResult,
)
from queo_data_platform.silver.service import (
    SilverLoadResult,
)


def build_pipeline_result() -> PipelineResult:
    bronze = BronzeLoadResult(
        discovered_file_count=2,
        successful_files=("tracker-01.csv",),
        skipped_files=("tracker-duplicate.csv",),
        failed_files=(),
        batch_ids=("batch-001",),
        inserted_row_count=10,
        duplicate_row_count=2,
    )

    silver = SilverLoadResult(
        mode="INCREMENTAL",
        batch_ids=("batch-001",),
        affected_event_dates=("2026-08-18",),
        affected_rejection_dates=("2026-08-18",),
        telemetry_rows_written=7,
        identity_rows_written=1,
        rejected_rows_written=2,
    )

    gold = GoldLoadResult(
        mode="INCREMENTAL",
        affected_event_dates=("2026-08-18",),
        affected_rejection_dates=("2026-08-18",),
        affected_quality_dates=("2026-08-18",),
        affected_devices=(
            "1001",
            "2002",
        ),
        dim_device_rows_written=2,
        last_position_rows_written=2,
        route_points_rows_written=7,
        daily_summary_rows_written=2,
        quality_summary_rows_written=1,
    )

    return PipelineResult(
        bronze=bronze,
        silver=silver,
        gold=gold,
    )


def test_format_pipeline_result_contains_layer_summary() -> None:
    result = build_pipeline_result()

    output = format_pipeline_result(result)

    assert "[BRONZE]" in output
    assert "[SILVER]" in output
    assert "[GOLD]" in output

    assert "inserted_rows=10" in output

    assert "mode=INCREMENTAL" in output

    assert "affected_devices=2" in output


def test_format_pipeline_result_contains_pipeline_status() -> None:
    result = build_pipeline_result()

    output = format_pipeline_result(result)

    assert "[PIPELINE] has_new_data=True" in output

    assert "[PIPELINE] has_changes=True" in output
