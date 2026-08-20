from typing import Annotated

from fastapi import Depends

from queo_data_platform.config.settings import (
    load_settings,
)
from queo_data_platform.query import (
    QueryService,
)


def get_query_service() -> QueryService:
    """
    Cria o serviço de consulta usando a configuração
    central da plataforma.
    """

    return QueryService.from_settings(load_settings())


type QueryServiceDependency = Annotated[
    QueryService,
    Depends(get_query_service),
]
