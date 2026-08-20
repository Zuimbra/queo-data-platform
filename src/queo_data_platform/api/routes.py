from datetime import date
from typing import Annotated

from fastapi import (
    APIRouter,
    HTTPException,
    Query,
)

from queo_data_platform.api.dependencies import (
    QueryServiceDependency,
)
from queo_data_platform.api.models import (
    DevicePageResponse,
    DeviceResponse,
    HealthResponse,
    LastPositionResponse,
    RoutePageResponse,
    RoutePointResponse,
)
from queo_data_platform.api.serialization import (
    dataframe_to_records,
)
from queo_data_platform.query.service import (
    DEFAULT_QUERY_LIMIT,
    MAX_QUERY_LIMIT,
)

router = APIRouter()


LimitParameter = Annotated[
    int,
    Query(
        ge=1,
        le=MAX_QUERY_LIMIT,
    ),
]

OffsetParameter = Annotated[
    int,
    Query(
        ge=0,
    ),
]


@router.get(
    "/health",
    response_model=HealthResponse,
    tags=["health"],
)
def health() -> HealthResponse:
    """
    Verifica apenas se o processo HTTP está ativo.

    Não depende da existência das tabelas Gold.
    """

    return HealthResponse(status="ok")


@router.get(
    "/api/v1/devices",
    response_model=DevicePageResponse,
    tags=["devices"],
)
def list_devices(
    service: QueryServiceDependency,
    limit: LimitParameter = DEFAULT_QUERY_LIMIT,
    offset: OffsetParameter = 0,
) -> DevicePageResponse:
    page = service.page_devices(
        limit=limit,
        offset=offset,
    )

    items = [
        DeviceResponse.model_validate(record)
        for record in dataframe_to_records(page.items)
    ]

    return DevicePageResponse(
        items=items,
        total=page.total,
        limit=page.limit,
        offset=page.offset,
        returned=page.returned,
        has_more=page.has_more,
        next_offset=page.next_offset,
    )


@router.get(
    "/api/v1/devices/{device_serial}",
    response_model=DeviceResponse,
    tags=["devices"],
)
def get_device(
    device_serial: str,
    service: QueryServiceDependency,
) -> DeviceResponse:
    dataframe = service.get_device(device_serial)

    if dataframe.empty:
        raise HTTPException(
            status_code=404,
            detail="Device not found.",
        )

    record = dataframe_to_records(dataframe)[0]

    return DeviceResponse.model_validate(record)


@router.get(
    "/api/v1/devices/{device_serial}/last-position",
    response_model=LastPositionResponse,
    tags=["positions"],
)
def get_last_position(
    device_serial: str,
    service: QueryServiceDependency,
) -> LastPositionResponse:
    dataframe = service.get_last_position(device_serial)

    if dataframe.empty:
        raise HTTPException(
            status_code=404,
            detail=("Last position not found."),
        )

    record = dataframe_to_records(dataframe)[0]

    return LastPositionResponse.model_validate(record)


@router.get(
    "/api/v1/devices/{device_serial}/route",
    response_model=RoutePageResponse,
    tags=["routes"],
)
def list_route_points(
    device_serial: str,
    service: QueryServiceDependency,
    start_date: date | None = None,
    end_date: date | None = None,
    limit: LimitParameter = DEFAULT_QUERY_LIMIT,
    offset: OffsetParameter = 0,
) -> RoutePageResponse:
    normalized_start_date = start_date.isoformat() if start_date is not None else None

    normalized_end_date = end_date.isoformat() if end_date is not None else None

    if start_date is not None and end_date is not None and start_date > end_date:
        raise HTTPException(
            status_code=422,
            detail=("start_date must be less than or equal to end_date."),
        )

    page = service.page_route_points(
        device_serial,
        start_date=normalized_start_date,
        end_date=normalized_end_date,
        limit=limit,
        offset=offset,
    )

    items = [
        RoutePointResponse.model_validate(record)
        for record in dataframe_to_records(page.items)
    ]

    return RoutePageResponse(
        items=items,
        total=page.total,
        limit=page.limit,
        offset=page.offset,
        returned=page.returned,
        has_more=page.has_more,
        next_offset=page.next_offset,
    )
