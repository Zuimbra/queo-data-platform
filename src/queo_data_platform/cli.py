from queo_data_platform.config.settings import (
    settings,
)
from queo_data_platform.pipeline.service import (
    PipelineResult,
    run_pipeline,
)


def format_pipeline_result(
    result: PipelineResult,
) -> str:
    """
    Formata um resumo legível da execução
    completa do pipeline.
    """

    bronze = result.bronze
    silver = result.silver
    gold = result.gold

    lines = [
        "[PIPELINE] Execution completed",
        "",
        "[BRONZE]",
        (f"  discovered_files={bronze.discovered_file_count}"),
        (f"  successful_files={len(bronze.successful_files)}"),
        (f"  skipped_files={len(bronze.skipped_files)}"),
        (f"  failed_files={len(bronze.failed_files)}"),
        (f"  inserted_rows={bronze.inserted_row_count}"),
        (f"  duplicate_rows={bronze.duplicate_row_count}"),
        (f"  propagated_batches={len(bronze.batch_ids)}"),
        "",
        "[SILVER]",
        f"  mode={silver.mode}",
        (f"  telemetry_rows={silver.telemetry_rows_written}"),
        (f"  identity_rows={silver.identity_rows_written}"),
        (f"  rejected_rows={silver.rejected_rows_written}"),
        (f"  affected_event_dates={len(silver.affected_event_dates)}"),
        (f"  affected_rejection_dates={len(silver.affected_rejection_dates)}"),
        "",
        "[GOLD]",
        f"  mode={gold.mode}",
        (f"  affected_devices={len(gold.affected_devices)}"),
        (f"  dim_device_rows={gold.dim_device_rows_written}"),
        (f"  last_position_rows={gold.last_position_rows_written}"),
        (f"  route_points_rows={gold.route_points_rows_written}"),
        (f"  daily_summary_rows={gold.daily_summary_rows_written}"),
        (f"  quality_summary_rows={gold.quality_summary_rows_written}"),
        "",
        (f"[PIPELINE] has_new_data={result.has_new_data}"),
        (f"[PIPELINE] has_changes={result.has_changes}"),
    ]

    return "\n".join(lines)


def main() -> None:
    """
    Executa o pipeline completo usando
    a configuração padrão da plataforma.
    """

    result = run_pipeline(settings)

    print(format_pipeline_result(result))
