from fastapi import (
    FastAPI,
    Request,
)
from fastapi.middleware.cors import (
    CORSMiddleware,
)
from fastapi.responses import (
    JSONResponse,
)

from queo_data_platform.api.routes import (
    router,
)
from queo_data_platform.config.settings import (
    Settings,
    load_settings,
)


def create_app(
    *,
    settings: Settings | None = None,
) -> FastAPI:
    """
    Cria a aplicação HTTP da plataforma.

    A factory facilita testes sem compartilhar
    estado global entre casos de teste.
    """

    resolved_settings = settings if settings is not None else load_settings()

    application = FastAPI(
        title="QUEO Data Platform API",
        version="0.1.0",
        description=("Read-only REST API for QUEO Data Platform Gold products."),
    )

    if resolved_settings.api_cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=list(resolved_settings.api_cors_origins),
            allow_credentials=False,
            allow_methods=[
                "GET",
            ],
            allow_headers=[
                "*",
            ],
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
