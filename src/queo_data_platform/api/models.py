from datetime import datetime

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class PageMetadata(BaseModel):
    total: int
    limit: int
    offset: int
    returned: int
    has_more: bool
    next_offset: int | None


class DeviceResponse(BaseModel):
    device_serial: str

    current_imei: str | None = None
    current_imsi: str | None = None
    current_iccid: str | None = None
    current_identity_auxiliary: str | None = None
    current_protocol_version: str | None = None

    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None

    first_identity_at: datetime | None = None
    last_identity_at: datetime | None = None

    first_telemetry_at: datetime | None = None
    last_telemetry_at: datetime | None = None

    identity_event_count: int | None = None
    telemetry_event_count: int | None = None

    has_identity_event: bool | None = None
    has_telemetry_event: bool | None = None

    current_imei_format_valid: bool | None = None
    current_imsi_format_valid: bool | None = None
    current_iccid_format_valid: bool | None = None


class DevicePageResponse(PageMetadata):
    items: list[DeviceResponse]


class LastPositionResponse(BaseModel):
    device_serial: str

    last_position_date: str | None = None
    last_position_at: datetime | None = None
    received_at: datetime | None = None

    latitude: float | None = None
    longitude: float | None = None
    speed: float | None = None
    direction_degrees: float | None = None

    battery_voltage: float | None = None
    internal_battery: float | None = None

    odometer_total: float | None = None
    horimeter: float | None = None

    hdop: float | None = None
    rx_level: float | None = None

    message_type: str | None = None
    report_type: int | None = None
    serial_count: int | None = None

    protocol_version: str | None = None
    position_quality: str | None = None
    source_file: str | None = None


class RoutePointResponse(BaseModel):
    event_date: str
    device_serial: str
    point_sequence: int

    event_timestamp: datetime
    received_at: datetime | None = None

    latitude: float | None = None
    longitude: float | None = None
    speed: float | None = None
    direction_degrees: float | None = None

    odometer_trip: float | None = None
    odometer_total: float | None = None
    horimeter: float | None = None

    hdop: float | None = None
    rx_level: float | None = None

    message_type: str | None = None
    report_type: int | None = None
    serial_count: int | None = None

    protocol_version: str | None = None
    position_quality: str | None = None
    is_moving: bool | None = None

    source_file: str | None = None


class RoutePageResponse(PageMetadata):
    items: list[RoutePointResponse]


class DailySummaryResponse(BaseModel):
    event_date: str
    device_serial: str

    first_event_at: datetime | None = None
    last_event_at: datetime | None = None

    message_count: int | None = None
    distinct_message_type_count: int | None = None

    valid_position_count: int | None = None
    invalid_position_count: int | None = None
    low_gps_precision_count: int | None = None

    valid_position_percentage: float | None = None

    moving_event_count: int | None = None
    stopped_event_count: int | None = None

    average_speed: float | None = None
    average_speed_while_moving: float | None = None
    maximum_speed: float | None = None

    average_hdop: float | None = None
    minimum_hdop: float | None = None
    maximum_hdop: float | None = None

    minimum_battery_voltage: float | None = None
    maximum_battery_voltage: float | None = None
    average_battery_voltage: float | None = None

    minimum_internal_battery: float | None = None
    maximum_internal_battery: float | None = None
    average_internal_battery: float | None = None

    first_odometer_total: float | None = None
    last_odometer_total: float | None = None
    odometer_delta_raw: float | None = None
    has_odometer_regression: bool | None = None

    first_valid_position_at: datetime | None = None
    last_valid_position_at: datetime | None = None

    first_latitude: float | None = None
    first_longitude: float | None = None
    last_latitude: float | None = None
    last_longitude: float | None = None


class DailySummaryPageResponse(PageMetadata):
    items: list[DailySummaryResponse]


class DataQualitySummaryResponse(BaseModel):
    metric_date: str

    telemetry_event_count: int | None = None
    identity_event_count: int | None = None
    accepted_event_count: int | None = None
    rejected_event_count: int | None = None
    total_event_count: int | None = None

    rejection_percentage: float | None = None

    missing_message_type_count: int | None = None
    invalid_message_type_count: int | None = None
    invalid_timestamp_count: int | None = None
    missing_device_serial_count: int | None = None
    unknown_rejection_count: int | None = None


class DataQualitySummaryPageResponse(PageMetadata):
    items: list[DataQualitySummaryResponse]
