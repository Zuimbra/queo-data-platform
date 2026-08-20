from fastapi import (
    FastAPI,
    Request,
)
from fastapi.responses import (
    JSONResponse,
)

from queo_data_platform.api.routes import (
    router,
)


def create_app() -> FastAPI:
    """
    Cria a aplicação HTTP da plataforma.

    A factory facilita testes sem compartilhar
    estado global entre casos de teste.
    """

    application = FastAPI(
        title="QUEO Data Platform API",
        version="0.1.0",
        description=("Read-only REST API for QUEO Data Platform Gold products."),
    )

    @application.exception_handler(FileNotFoundError)
    async def handle_missing_gold_table(
        _request: Request,
        _error: FileNotFoundError,
    ) -> JSONResponse:
        """
        Não expõe caminhos físicos do Lakehouse
        ao consumidor HTTP.
        """

        return JSONResponse(
            status_code=503,
            content={"detail": ("Gold data is not available.")},
        )

    @application.exception_handler(ValueError)
    async def handle_value_error(
        _request: Request,
        error: ValueError,
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": str(error)},
        )

    application.include_router(router)

    return application


app = create_app()
