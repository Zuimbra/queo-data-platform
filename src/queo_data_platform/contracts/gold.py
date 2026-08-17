import pyarrow as pa

DIM_DEVICE_TABLE_NAME = "dim_device"

DEVICE_LAST_POSITION_TABLE_NAME = "device_last_position"

DEVICE_ROUTE_POINTS_TABLE_NAME = "device_route_points"

DEVICE_DAILY_SUMMARY_TABLE_NAME = "device_daily_summary"

DATA_QUALITY_SUMMARY_TABLE_NAME = "data_quality_summary"


GOLD_EVENT_PARTITION_COLUMN = "event_date"

GOLD_QUALITY_PARTITION_COLUMN = "metric_date"

GOLD_DEVICE_KEY = "device_serial"


GOLD_TIMESTAMP = pa.timestamp("us")


DIM_DEVICE_SCHEMA = pa.schema(
    [
        pa.field(
            "device_serial",
            pa.string(),
        ),
        pa.field(
            "current_imei",
            pa.string(),
        ),
        pa.field(
            "current_imsi",
            pa.string(),
        ),
        pa.field(
            "current_iccid",
            pa.string(),
        ),
        pa.field(
            "current_identity_auxiliary",
            pa.string(),
        ),
        pa.field(
            "current_protocol_version",
            pa.string(),
        ),
        pa.field(
            "first_seen_at",
            GOLD_TIMESTAMP,
        ),
        pa.field(
            "last_seen_at",
            GOLD_TIMESTAMP,
        ),
        pa.field(
            "first_identity_at",
            GOLD_TIMESTAMP,
        ),
        pa.field(
            "last_identity_at",
            GOLD_TIMESTAMP,
        ),
        pa.field(
            "first_telemetry_at",
            GOLD_TIMESTAMP,
        ),
        pa.field(
            "last_telemetry_at",
            GOLD_TIMESTAMP,
        ),
        pa.field(
            "identity_event_count",
            pa.int64(),
        ),
        pa.field(
            "telemetry_event_count",
            pa.int64(),
        ),
        pa.field(
            "has_identity_event",
            pa.bool_(),
        ),
        pa.field(
            "has_telemetry_event",
            pa.bool_(),
        ),
        pa.field(
            "current_imei_format_valid",
            pa.bool_(),
        ),
        pa.field(
            "current_imsi_format_valid",
            pa.bool_(),
        ),
        pa.field(
            "current_iccid_format_valid",
            pa.bool_(),
        ),
    ]
)


DEVICE_LAST_POSITION_SCHEMA = pa.schema(
    [
        pa.field(
            "device_serial",
            pa.string(),
        ),
        pa.field(
            "last_position_date",
            pa.string(),
        ),
        pa.field(
            "last_position_at",
            GOLD_TIMESTAMP,
        ),
        pa.field(
            "received_at",
            GOLD_TIMESTAMP,
        ),
        pa.field(
            "latitude",
            pa.float64(),
        ),
        pa.field(
            "longitude",
            pa.float64(),
        ),
        pa.field(
            "speed",
            pa.float64(),
        ),
        pa.field(
            "direction_degrees",
            pa.float64(),
        ),
        pa.field(
            "battery_voltage",
            pa.float64(),
        ),
        pa.field(
            "internal_battery",
            pa.float64(),
        ),
        pa.field(
            "odometer_total",
            pa.float64(),
        ),
        pa.field(
            "horimeter",
            pa.float64(),
        ),
        pa.field(
            "hdop",
            pa.float64(),
        ),
        pa.field(
            "rx_level",
            pa.float64(),
        ),
        pa.field(
            "message_type",
            pa.string(),
        ),
        pa.field(
            "report_type",
            pa.int32(),
        ),
        pa.field(
            "serial_count",
            pa.int64(),
        ),
        pa.field(
            "protocol_version",
            pa.string(),
        ),
        pa.field(
            "position_quality",
            pa.string(),
        ),
        pa.field(
            "source_file",
            pa.string(),
        ),
    ]
)


DEVICE_ROUTE_POINTS_SCHEMA = pa.schema(
    [
        pa.field(
            "event_date",
            pa.string(),
        ),
        pa.field(
            "device_serial",
            pa.string(),
        ),
        pa.field(
            "point_sequence",
            pa.int64(),
        ),
        pa.field(
            "event_timestamp",
            GOLD_TIMESTAMP,
        ),
        pa.field(
            "received_at",
            GOLD_TIMESTAMP,
        ),
        pa.field(
            "latitude",
            pa.float64(),
        ),
        pa.field(
            "longitude",
            pa.float64(),
        ),
        pa.field(
            "speed",
            pa.float64(),
        ),
        pa.field(
            "direction_degrees",
            pa.float64(),
        ),
        pa.field(
            "odometer_trip",
            pa.float64(),
        ),
        pa.field(
            "odometer_total",
            pa.float64(),
        ),
        pa.field(
            "horimeter",
            pa.float64(),
        ),
        pa.field(
            "hdop",
            pa.float64(),
        ),
        pa.field(
            "rx_level",
            pa.float64(),
        ),
        pa.field(
            "message_type",
            pa.string(),
        ),
        pa.field(
            "report_type",
            pa.int32(),
        ),
        pa.field(
            "serial_count",
            pa.int64(),
        ),
        pa.field(
            "protocol_version",
            pa.string(),
        ),
        pa.field(
            "position_quality",
            pa.string(),
        ),
        pa.field(
            "is_moving",
            pa.bool_(),
        ),
        pa.field(
            "source_file",
            pa.string(),
        ),
    ]
)


DEVICE_DAILY_SUMMARY_SCHEMA = pa.schema(
    [
        pa.field(
            "event_date",
            pa.string(),
        ),
        pa.field(
            "device_serial",
            pa.string(),
        ),
        pa.field(
            "first_event_at",
            GOLD_TIMESTAMP,
        ),
        pa.field(
            "last_event_at",
            GOLD_TIMESTAMP,
        ),
        pa.field(
            "message_count",
            pa.int64(),
        ),
        pa.field(
            "distinct_message_type_count",
            pa.int64(),
        ),
        pa.field(
            "valid_position_count",
            pa.int64(),
        ),
        pa.field(
            "invalid_position_count",
            pa.int64(),
        ),
        pa.field(
            "low_gps_precision_count",
            pa.int64(),
        ),
        pa.field(
            "valid_position_percentage",
            pa.float64(),
        ),
        pa.field(
            "moving_event_count",
            pa.int64(),
        ),
        pa.field(
            "stopped_event_count",
            pa.int64(),
        ),
        pa.field(
            "average_speed",
            pa.float64(),
        ),
        pa.field(
            "average_speed_while_moving",
            pa.float64(),
        ),
        pa.field(
            "maximum_speed",
            pa.float64(),
        ),
        pa.field(
            "average_hdop",
            pa.float64(),
        ),
        pa.field(
            "minimum_hdop",
            pa.float64(),
        ),
        pa.field(
            "maximum_hdop",
            pa.float64(),
        ),
        pa.field(
            "minimum_battery_voltage",
            pa.float64(),
        ),
        pa.field(
            "maximum_battery_voltage",
            pa.float64(),
        ),
        pa.field(
            "average_battery_voltage",
            pa.float64(),
        ),
        pa.field(
            "minimum_internal_battery",
            pa.float64(),
        ),
        pa.field(
            "maximum_internal_battery",
            pa.float64(),
        ),
        pa.field(
            "average_internal_battery",
            pa.float64(),
        ),
        pa.field(
            "first_odometer_total",
            pa.float64(),
        ),
        pa.field(
            "last_odometer_total",
            pa.float64(),
        ),
        pa.field(
            "odometer_delta_raw",
            pa.float64(),
        ),
        pa.field(
            "has_odometer_regression",
            pa.bool_(),
        ),
        pa.field(
            "first_valid_position_at",
            GOLD_TIMESTAMP,
        ),
        pa.field(
            "last_valid_position_at",
            GOLD_TIMESTAMP,
        ),
        pa.field(
            "first_latitude",
            pa.float64(),
        ),
        pa.field(
            "first_longitude",
            pa.float64(),
        ),
        pa.field(
            "last_latitude",
            pa.float64(),
        ),
        pa.field(
            "last_longitude",
            pa.float64(),
        ),
    ]
)


DATA_QUALITY_SUMMARY_SCHEMA = pa.schema(
    [
        pa.field(
            "metric_date",
            pa.string(),
        ),
        pa.field(
            "telemetry_event_count",
            pa.int64(),
        ),
        pa.field(
            "identity_event_count",
            pa.int64(),
        ),
        pa.field(
            "accepted_event_count",
            pa.int64(),
        ),
        pa.field(
            "rejected_event_count",
            pa.int64(),
        ),
        pa.field(
            "total_event_count",
            pa.int64(),
        ),
        pa.field(
            "rejection_percentage",
            pa.float64(),
        ),
        pa.field(
            "missing_message_type_count",
            pa.int64(),
        ),
        pa.field(
            "invalid_message_type_count",
            pa.int64(),
        ),
        pa.field(
            "invalid_timestamp_count",
            pa.int64(),
        ),
        pa.field(
            "missing_device_serial_count",
            pa.int64(),
        ),
        pa.field(
            "unknown_rejection_count",
            pa.int64(),
        ),
    ]
)


GOLD_PARTITIONED_TABLES = {
    DEVICE_ROUTE_POINTS_TABLE_NAME: (GOLD_EVENT_PARTITION_COLUMN),
    DEVICE_DAILY_SUMMARY_TABLE_NAME: (GOLD_EVENT_PARTITION_COLUMN),
    DATA_QUALITY_SUMMARY_TABLE_NAME: (GOLD_QUALITY_PARTITION_COLUMN),
}


GOLD_ENTITY_TABLES = (
    DIM_DEVICE_TABLE_NAME,
    DEVICE_LAST_POSITION_TABLE_NAME,
)


GOLD_TABLE_SCHEMAS = {
    DIM_DEVICE_TABLE_NAME: (DIM_DEVICE_SCHEMA),
    DEVICE_LAST_POSITION_TABLE_NAME: (DEVICE_LAST_POSITION_SCHEMA),
    DEVICE_ROUTE_POINTS_TABLE_NAME: (DEVICE_ROUTE_POINTS_SCHEMA),
    DEVICE_DAILY_SUMMARY_TABLE_NAME: (DEVICE_DAILY_SUMMARY_SCHEMA),
    DATA_QUALITY_SUMMARY_TABLE_NAME: (DATA_QUALITY_SUMMARY_SCHEMA),
}
