from dataclasses import dataclass

from queo_data_platform.bronze.service import (
    BronzeLoadResult,
    load_bronze,
)
from queo_data_platform.config.settings import Settings
from queo_data_platform.contracts.tracker import (
    BRONZE_TABLE_NAME,
)
from queo_data_platform.gold.service import (
    GoldLoadResult,
    load_gold,
)
from queo_data_platform.infrastructure.delta.table import (
    is_delta_table,
)
from queo_data_platform.silver.service import (
    SilverLoadResult,
    load_silver,
)


@dataclass(frozen=True)
class PipelineResult:
    """
    Resultado consolidado de uma execução
    Bronze -> Silver -> Gold.
    """

    bronze: BronzeLoadResult
    silver: SilverLoadResult
    gold: GoldLoadResult

    @property
    def has_new_data(self) -> bool:
        """
        Indica se novas linhas foram inseridas
        na camada Bronze.
        """

        return self.bronze.has_new_data

    @property
    def has_changes(self) -> bool:
        """
        Indica se alguma camada sofreu alteração.

        Também considera rebuilds de recuperação
        da Silver ou Gold.
        """

        return (
            self.bronze.has_new_data or self.silver.has_changes or self.gold.has_changes
        )


def build_initial_noop_silver_result() -> SilverLoadResult:
    """
    Representa uma Silver não executada porque
    ainda não existe uma Bronze para processar.
    """

    return SilverLoadResult(
        mode="NOOP",
        batch_ids=(),
        affected_event_dates=(),
        affected_rejection_dates=(),
        telemetry_rows_written=0,
        identity_rows_written=0,
        rejected_rows_written=0,
    )


def build_initial_noop_gold_result() -> GoldLoadResult:
    """
    Representa uma Gold não executada porque
    ainda não existem fontes Silver.
    """

    return GoldLoadResult(
        mode="NOOP",
        affected_event_dates=(),
        affected_rejection_dates=(),
        affected_quality_dates=(),
        affected_devices=(),
        dim_device_rows_written=0,
        last_position_rows_written=0,
        route_points_rows_written=0,
        daily_summary_rows_written=0,
        quality_summary_rows_written=0,
    )


def run_pipeline(
    settings: Settings,
) -> PipelineResult:
    """
    Executa o pipeline completo:

        Bronze
          ↓
        Silver
          ↓
        Gold

    Caso seja a primeira execução, o inbox esteja vazio
    e ainda não exista uma Bronze persistida, Silver e
    Gold não são executadas e retornam NOOP.
    """

    bronze_result = load_bronze(settings)

    bronze_path = settings.bronze_dir / BRONZE_TABLE_NAME

    if not is_delta_table(bronze_path):
        return PipelineResult(
            bronze=bronze_result,
            silver=(build_initial_noop_silver_result()),
            gold=(build_initial_noop_gold_result()),
        )

    silver_result = load_silver(
        settings,
        batch_ids=(bronze_result.batch_ids),
    )

    gold_result = load_gold(
        settings,
        silver_result=silver_result,
    )

    return PipelineResult(
        bronze=bronze_result,
        silver=silver_result,
        gold=gold_result,
    )
