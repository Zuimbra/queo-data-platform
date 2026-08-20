from dataclasses import dataclass
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd
from deltalake import DeltaTable

from queo_data_platform.config.settings import Settings
from queo_data_platform.contracts.gold import (
    DATA_QUALITY_SUMMARY_TABLE_NAME,
    DEVICE_DAILY_SUMMARY_TABLE_NAME,
    DEVICE_LAST_POSITION_TABLE_NAME,
    DEVICE_ROUTE_POINTS_TABLE_NAME,
    DIM_DEVICE_TABLE_NAME,
)
from queo_data_platform.infrastructure.delta.table import (
    is_delta_table,
)

DEFAULT_QUERY_LIMIT = 100

MAX_QUERY_LIMIT = 1000


@dataclass(frozen=True)
class QueryPaths:
    """
    Caminhos físicos dos produtos Gold disponíveis
    para consumo pela Query Layer.
    """

    dim_device: Path
    last_position: Path
    route_points: Path
    daily_summary: Path
    quality_summary: Path


@dataclass(frozen=True)
class QueryPage:
    """
    Resultado paginado produzido pela Query Layer.

    items:
        registros da página atual.

    total:
        quantidade total de registros que atendem
        aos mesmos filtros, antes de LIMIT/OFFSET.

    limit / offset:
        parâmetros efetivamente utilizados.
    """

    items: pd.DataFrame
    total: int
    limit: int
    offset: int

    @property
    def returned(self) -> int:
        return len(self.items)

    @property
    def has_more(self) -> bool:
        return self.offset + self.returned < self.total

    @property
    def next_offset(self) -> int | None:
        if not self.has_more:
            return None

        return self.offset + self.returned


def get_query_paths(
    gold_dir: Path,
) -> QueryPaths:
    """
    Resolve os caminhos físicos das cinco
    Delta Tables Gold.
    """

    return QueryPaths(
        dim_device=(gold_dir / DIM_DEVICE_TABLE_NAME),
        last_position=(gold_dir / DEVICE_LAST_POSITION_TABLE_NAME),
        route_points=(gold_dir / DEVICE_ROUTE_POINTS_TABLE_NAME),
        daily_summary=(gold_dir / DEVICE_DAILY_SUMMARY_TABLE_NAME),
        quality_summary=(gold_dir / DATA_QUALITY_SUMMARY_TABLE_NAME),
    )


def normalize_required_text(
    value: str,
    *,
    field_name: str,
) -> str:
    """
    Normaliza valores textuais obrigatórios usados
    como filtros de consulta.
    """

    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{field_name} must not be empty.")

    return normalized


def normalize_pagination(
    *,
    limit: int,
    offset: int,
) -> tuple[int, int]:
    """
    Valida paginação usada pelas consultas públicas.

    limit:
        deve ficar entre 1 e MAX_QUERY_LIMIT.

    offset:
        deve ser maior ou igual a zero.
    """

    if isinstance(limit, bool) or not isinstance(
        limit,
        int,
    ):
        raise TypeError("limit must be an integer.")

    if limit < 1:
        raise ValueError("limit must be greater than zero.")

    if limit > MAX_QUERY_LIMIT:
        raise ValueError(f"limit must not exceed {MAX_QUERY_LIMIT}.")

    if isinstance(offset, bool) or not isinstance(
        offset,
        int,
    ):
        raise TypeError("offset must be an integer.")

    if offset < 0:
        raise ValueError("offset must be greater than or equal to zero.")

    return (
        limit,
        offset,
    )


def normalize_optional_date(
    value: str | None,
    *,
    field_name: str,
) -> str | None:
    """
    Valida filtros opcionais de data no formato:

        YYYY-MM-DD
    """

    if value is None:
        return None

    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{field_name} must not be empty.")

    try:
        date.fromisoformat(normalized)

    except ValueError as error:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format.") from error

    return normalized


def load_query_table(
    table_path: Path,
) -> DeltaTable:
    """
    Carrega uma Delta Table Gold somente depois
    de validar sua existência.

    A Query Layer não cria produtos ausentes.
    Ela apenas consome produtos já publicados
    pela Gold.
    """

    if not is_delta_table(table_path):
        raise FileNotFoundError(f"Gold Delta Table does not exist: {table_path}")

    return DeltaTable(str(table_path))


def execute_gold_query(
    *,
    table_path: Path,
    relation_name: str,
    sql: str,
    parameters: list[object] | None = None,
) -> pd.DataFrame:
    """
    Executa uma consulta controlada sobre uma
    Delta Table Gold.

    A Delta Table é registrada no DuckDB através
    de seu PyArrow Dataset.

    A conexão é criada e fechada dentro da própria
    consulta para evitar estado compartilhado entre
    requisições futuras da API ou MCP.
    """

    table = load_query_table(table_path)

    connection = duckdb.connect()

    try:
        connection.register(
            relation_name,
            table.to_pyarrow_dataset(),
        )

        if parameters is None:
            return connection.execute(sql).df()

        return connection.execute(
            sql,
            parameters,
        ).df()

    finally:
        connection.close()


def execute_gold_count(
    *,
    table_path: Path,
    relation_name: str,
    sql: str,
    parameters: list[object] | None = None,
) -> int:
    """
    Executa uma consulta COUNT controlada sobre
    uma tabela Gold.

    O SQL recebido deve retornar uma coluna:

        total_count
    """

    result = execute_gold_query(
        table_path=table_path,
        relation_name=relation_name,
        sql=sql,
        parameters=parameters,
    )

    if result.empty:
        return 0

    return int(
        result.loc[
            0,
            "total_count",
        ]
    )


@dataclass(frozen=True)
class QueryService:
    """
    Interface de leitura dos produtos Gold.

    Esta classe é deliberadamente read-only.

    Ela será reutilizada posteriormente por:

        REST API
        MCP
        outros consumidores internos

    sem permitir que esses consumidores conheçam
    detalhes físicos das Delta Tables.
    """

    gold_dir: Path

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
    ) -> QueryService:
        """
        Cria o serviço utilizando a configuração
        central da plataforma.
        """

        return cls(gold_dir=settings.gold_dir)

    @property
    def paths(self) -> QueryPaths:
        """
        Resolve os caminhos Gold usados pelo serviço.
        """

        return get_query_paths(self.gold_dir)

    def list_devices(
        self,
        *,
        limit: int = DEFAULT_QUERY_LIMIT,
        offset: int = 0,
    ) -> pd.DataFrame:
        """
        Lista dispositivos conhecidos pela Gold.

        A ordenação por device_serial torna a
        paginação determinística.
        """

        normalized_limit, normalized_offset = normalize_pagination(
            limit=limit,
            offset=offset,
        )

        return execute_gold_query(
            table_path=self.paths.dim_device,
            relation_name="query_dim_device",
            sql=f"""
                SELECT
                    *

                FROM query_dim_device

                ORDER BY
                    device_serial

                LIMIT {normalized_limit}
                OFFSET {normalized_offset}
            """,
        )

    def get_device(
        self,
        device_serial: str,
    ) -> pd.DataFrame:
        """
        Retorna um dispositivo específico.

        Quando o dispositivo não existe,
        retorna um DataFrame vazio.
        """

        normalized_device_serial = normalize_required_text(
            device_serial,
            field_name="device_serial",
        )

        return execute_gold_query(
            table_path=self.paths.dim_device,
            relation_name="query_dim_device",
            sql="""
                SELECT
                    *

                FROM query_dim_device

                WHERE
                    device_serial = ?

                LIMIT 1
            """,
            parameters=[normalized_device_serial],
        )

    def list_last_positions(
        self,
        *,
        device_serial: str | None = None,
        limit: int = DEFAULT_QUERY_LIMIT,
        offset: int = 0,
    ) -> pd.DataFrame:
        """
        Lista as últimas posições dos dispositivos.

        Pode opcionalmente filtrar por um único
        device_serial.
        """

        normalized_limit, normalized_offset = normalize_pagination(
            limit=limit,
            offset=offset,
        )

        if device_serial is None:
            return execute_gold_query(
                table_path=(self.paths.last_position),
                relation_name=("query_last_position"),
                sql=f"""
                    SELECT
                        *

                    FROM query_last_position

                    ORDER BY
                        last_position_at DESC,
                        device_serial

                    LIMIT {normalized_limit}
                    OFFSET {normalized_offset}
                """,
            )

        normalized_device_serial = normalize_required_text(
            device_serial,
            field_name="device_serial",
        )

        return execute_gold_query(
            table_path=(self.paths.last_position),
            relation_name=("query_last_position"),
            sql=f"""
                SELECT
                    *

                FROM query_last_position

                WHERE
                    device_serial = ?

                ORDER BY
                    last_position_at DESC,
                    device_serial

                LIMIT {normalized_limit}
                OFFSET {normalized_offset}
            """,
            parameters=[normalized_device_serial],
        )

    def get_last_position(
        self,
        device_serial: str,
    ) -> pd.DataFrame:
        """
        Retorna a última posição publicada pela Gold
        para um dispositivo.

        device_last_position possui no máximo uma linha
        por dispositivo.
        """

        normalized_device_serial = normalize_required_text(
            device_serial,
            field_name="device_serial",
        )

        return execute_gold_query(
            table_path=(self.paths.last_position),
            relation_name=("query_last_position"),
            sql="""
                SELECT
                    *

                FROM query_last_position

                WHERE
                    device_serial = ?

                LIMIT 1
            """,
            parameters=[normalized_device_serial],
        )

    def list_route_points(
        self,
        device_serial: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = DEFAULT_QUERY_LIMIT,
        offset: int = 0,
    ) -> pd.DataFrame:
        """
        Lista pontos de rota de um dispositivo.

        Os filtros start_date/end_date utilizam
        event_date, que é a coluna de partição
        física da tabela Gold.

        Isso prepara a consulta para aproveitar
        pruning/pushdown das partições durante
        leituras futuras de maior volume.
        """

        normalized_device_serial = normalize_required_text(
            device_serial,
            field_name="device_serial",
        )

        normalized_start_date = normalize_optional_date(
            start_date,
            field_name="start_date",
        )

        normalized_end_date = normalize_optional_date(
            end_date,
            field_name="end_date",
        )

        if (
            normalized_start_date is not None
            and normalized_end_date is not None
            and normalized_start_date > normalized_end_date
        ):
            raise ValueError("start_date must be less than or equal to end_date.")

        normalized_limit, normalized_offset = normalize_pagination(
            limit=limit,
            offset=offset,
        )

        filters = [
            "device_serial = ?",
        ]

        parameters: list[object] = [
            normalized_device_serial,
        ]

        if normalized_start_date is not None:
            filters.append("event_date >= ?")

            parameters.append(normalized_start_date)

        if normalized_end_date is not None:
            filters.append("event_date <= ?")

            parameters.append(normalized_end_date)

        where_clause = "\nAND ".join(filters)

        return execute_gold_query(
            table_path=(self.paths.route_points),
            relation_name=("query_route_points"),
            sql=f"""
                SELECT
                    *

                FROM query_route_points

                WHERE
                    {where_clause}

                ORDER BY
                    event_timestamp,
                    point_sequence

                LIMIT {normalized_limit}
                OFFSET {normalized_offset}
            """,
            parameters=parameters,
        )

    def page_devices(
        self,
        *,
        limit: int = DEFAULT_QUERY_LIMIT,
        offset: int = 0,
    ) -> QueryPage:
        """
        Retorna dispositivos junto dos metadados
        necessários para paginação.
        """

        normalized_limit, normalized_offset = normalize_pagination(
            limit=limit,
            offset=offset,
        )

        items = self.list_devices(
            limit=normalized_limit,
            offset=normalized_offset,
        )

        total = execute_gold_count(
            table_path=self.paths.dim_device,
            relation_name=("query_dim_device"),
            sql="""
                SELECT
                    COUNT(*) AS total_count

                FROM query_dim_device
            """,
        )

        return QueryPage(
            items=items,
            total=total,
            limit=normalized_limit,
            offset=normalized_offset,
        )

    def page_last_positions(
        self,
        *,
        device_serial: str | None = None,
        limit: int = DEFAULT_QUERY_LIMIT,
        offset: int = 0,
    ) -> QueryPage:
        """
        Retorna últimas posições com metadados
        de paginação.
        """

        normalized_limit, normalized_offset = normalize_pagination(
            limit=limit,
            offset=offset,
        )

        items = self.list_last_positions(
            device_serial=device_serial,
            limit=normalized_limit,
            offset=normalized_offset,
        )

        if device_serial is None:
            total = execute_gold_count(
                table_path=(self.paths.last_position),
                relation_name=("query_last_position"),
                sql="""
                    SELECT
                        COUNT(*) AS total_count

                    FROM query_last_position
                """,
            )

        else:
            normalized_device_serial = normalize_required_text(
                device_serial,
                field_name=("device_serial"),
            )

            total = execute_gold_count(
                table_path=(self.paths.last_position),
                relation_name=("query_last_position"),
                sql="""
                    SELECT
                        COUNT(*) AS total_count

                    FROM query_last_position

                    WHERE
                        device_serial = ?
                """,
                parameters=[normalized_device_serial],
            )

        return QueryPage(
            items=items,
            total=total,
            limit=normalized_limit,
            offset=normalized_offset,
        )

    def page_route_points(
        self,
        device_serial: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = DEFAULT_QUERY_LIMIT,
        offset: int = 0,
    ) -> QueryPage:
        """
        Retorna uma página da rota e a quantidade
        total de pontos que atendem aos filtros.
        """

        normalized_device_serial = normalize_required_text(
            device_serial,
            field_name="device_serial",
        )

        normalized_start_date = normalize_optional_date(
            start_date,
            field_name="start_date",
        )

        normalized_end_date = normalize_optional_date(
            end_date,
            field_name="end_date",
        )

        if (
            normalized_start_date is not None
            and normalized_end_date is not None
            and normalized_start_date > normalized_end_date
        ):
            raise ValueError("start_date must be less than or equal to end_date.")

        normalized_limit, normalized_offset = normalize_pagination(
            limit=limit,
            offset=offset,
        )

        items = self.list_route_points(
            normalized_device_serial,
            start_date=(normalized_start_date),
            end_date=normalized_end_date,
            limit=normalized_limit,
            offset=normalized_offset,
        )

        filters = [
            "device_serial = ?",
        ]

        parameters: list[object] = [
            normalized_device_serial,
        ]

        if normalized_start_date is not None:
            filters.append("event_date >= ?")
            parameters.append(normalized_start_date)

        if normalized_end_date is not None:
            filters.append("event_date <= ?")
            parameters.append(normalized_end_date)

        where_clause = "\nAND ".join(filters)

        total = execute_gold_count(
            table_path=(self.paths.route_points),
            relation_name=("query_route_points"),
            sql=f"""
                SELECT
                    COUNT(*) AS total_count

                FROM query_route_points

                WHERE
                    {where_clause}
            """,
            parameters=parameters,
        )

        return QueryPage(
            items=items,
            total=total,
            limit=normalized_limit,
            offset=normalized_offset,
        )

    def list_daily_summaries(
        self,
        *,
        device_serial: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = DEFAULT_QUERY_LIMIT,
        offset: int = 0,
    ) -> pd.DataFrame:
        """
        Consulta os resumos operacionais diários
        produzidos pela Gold.

        Pode filtrar por:

            device_serial
            start_date
            end_date
        """

        normalized_start_date = normalize_optional_date(
            start_date,
            field_name="start_date",
        )

        normalized_end_date = normalize_optional_date(
            end_date,
            field_name="end_date",
        )

        if (
            normalized_start_date is not None
            and normalized_end_date is not None
            and normalized_start_date > normalized_end_date
        ):
            raise ValueError("start_date must be less than or equal to end_date.")

        normalized_limit, normalized_offset = normalize_pagination(
            limit=limit,
            offset=offset,
        )

        filters: list[str] = []

        parameters: list[object] = []

        if device_serial is not None:
            normalized_device_serial = normalize_required_text(
                device_serial,
                field_name=("device_serial"),
            )

            filters.append("device_serial = ?")

            parameters.append(normalized_device_serial)

        if normalized_start_date is not None:
            filters.append("event_date >= ?")

            parameters.append(normalized_start_date)

        if normalized_end_date is not None:
            filters.append("event_date <= ?")

            parameters.append(normalized_end_date)

        where_clause = "TRUE"

        if filters:
            where_clause = "\nAND ".join(filters)

        return execute_gold_query(
            table_path=(self.paths.daily_summary),
            relation_name=("query_daily_summary"),
            sql=f"""
                SELECT
                    *

                FROM query_daily_summary

                WHERE
                    {where_clause}

                ORDER BY
                    event_date DESC,
                    device_serial

                LIMIT {normalized_limit}
                OFFSET {normalized_offset}
            """,
            parameters=parameters,
        )

    def page_daily_summaries(
        self,
        *,
        device_serial: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = DEFAULT_QUERY_LIMIT,
        offset: int = 0,
    ) -> QueryPage:
        """
        Retorna os resumos diários com metadados
        completos de paginação.
        """

        normalized_start_date = normalize_optional_date(
            start_date,
            field_name="start_date",
        )

        normalized_end_date = normalize_optional_date(
            end_date,
            field_name="end_date",
        )

        if (
            normalized_start_date is not None
            and normalized_end_date is not None
            and normalized_start_date > normalized_end_date
        ):
            raise ValueError("start_date must be less than or equal to end_date.")

        normalized_limit, normalized_offset = normalize_pagination(
            limit=limit,
            offset=offset,
        )

        items = self.list_daily_summaries(
            device_serial=device_serial,
            start_date=(normalized_start_date),
            end_date=normalized_end_date,
            limit=normalized_limit,
            offset=normalized_offset,
        )

        filters: list[str] = []

        parameters: list[object] = []

        if device_serial is not None:
            normalized_device_serial = normalize_required_text(
                device_serial,
                field_name=("device_serial"),
            )

            filters.append("device_serial = ?")

            parameters.append(normalized_device_serial)

        if normalized_start_date is not None:
            filters.append("event_date >= ?")

            parameters.append(normalized_start_date)

        if normalized_end_date is not None:
            filters.append("event_date <= ?")

            parameters.append(normalized_end_date)

        where_clause = "TRUE"

        if filters:
            where_clause = "\nAND ".join(filters)

        total = execute_gold_count(
            table_path=(self.paths.daily_summary),
            relation_name=("query_daily_summary"),
            sql=f"""
                SELECT
                    COUNT(*) AS total_count

                FROM query_daily_summary

                WHERE
                    {where_clause}
            """,
            parameters=parameters,
        )

        return QueryPage(
            items=items,
            total=total,
            limit=normalized_limit,
            offset=normalized_offset,
        )

    def list_quality_summaries(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = DEFAULT_QUERY_LIMIT,
        offset: int = 0,
    ) -> pd.DataFrame:
        """
        Consulta as métricas diárias de qualidade
        produzidas pela Gold.
        """

        normalized_start_date = normalize_optional_date(
            start_date,
            field_name="start_date",
        )

        normalized_end_date = normalize_optional_date(
            end_date,
            field_name="end_date",
        )

        if (
            normalized_start_date is not None
            and normalized_end_date is not None
            and normalized_start_date > normalized_end_date
        ):
            raise ValueError("start_date must be less than or equal to end_date.")

        normalized_limit, normalized_offset = normalize_pagination(
            limit=limit,
            offset=offset,
        )

        filters: list[str] = []

        parameters: list[object] = []

        if normalized_start_date is not None:
            filters.append("metric_date >= ?")

            parameters.append(normalized_start_date)

        if normalized_end_date is not None:
            filters.append("metric_date <= ?")

            parameters.append(normalized_end_date)

        where_clause = "TRUE"

        if filters:
            where_clause = "\nAND ".join(filters)

        return execute_gold_query(
            table_path=(self.paths.quality_summary),
            relation_name=("query_quality_summary"),
            sql=f"""
                SELECT
                    *

                FROM query_quality_summary

                WHERE
                    {where_clause}

                ORDER BY
                    metric_date DESC

                LIMIT {normalized_limit}
                OFFSET {normalized_offset}
            """,
            parameters=parameters,
        )

    def page_quality_summaries(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int = DEFAULT_QUERY_LIMIT,
        offset: int = 0,
    ) -> QueryPage:
        """
        Retorna métricas de qualidade com
        metadados de paginação.
        """

        normalized_start_date = normalize_optional_date(
            start_date,
            field_name="start_date",
        )

        normalized_end_date = normalize_optional_date(
            end_date,
            field_name="end_date",
        )

        if (
            normalized_start_date is not None
            and normalized_end_date is not None
            and normalized_start_date > normalized_end_date
        ):
            raise ValueError("start_date must be less than or equal to end_date.")

        normalized_limit, normalized_offset = normalize_pagination(
            limit=limit,
            offset=offset,
        )

        items = self.list_quality_summaries(
            start_date=(normalized_start_date),
            end_date=normalized_end_date,
            limit=normalized_limit,
            offset=normalized_offset,
        )

        filters: list[str] = []

        parameters: list[object] = []

        if normalized_start_date is not None:
            filters.append("metric_date >= ?")

            parameters.append(normalized_start_date)

        if normalized_end_date is not None:
            filters.append("metric_date <= ?")

            parameters.append(normalized_end_date)

        where_clause = "TRUE"

        if filters:
            where_clause = "\nAND ".join(filters)

        total = execute_gold_count(
            table_path=(self.paths.quality_summary),
            relation_name=("query_quality_summary"),
            sql=f"""
                SELECT
                    COUNT(*) AS total_count

                FROM query_quality_summary

                WHERE
                    {where_clause}
            """,
            parameters=parameters,
        )

        return QueryPage(
            items=items,
            total=total,
            limit=normalized_limit,
            offset=normalized_offset,
        )
