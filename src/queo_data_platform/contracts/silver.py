import pyarrow as pa

from queo_data_platform.contracts.tracker import (
    BRONZE_METADATA_COLUMNS,
)

TELEMETRY_TABLE_NAME = "telemetry_events"

DEVICE_IDENTITY_TABLE_NAME = "device_identity_events"

REJECTED_LOGS_TABLE_NAME = "rejected_logs"


SILVER_EVENT_PARTITION_COLUMN = "event_date"

SILVER_REJECTION_PARTITION_COLUMN = "rejection_date"


# A Silver deve preservar a linhagem criada pela Bronze.
#
# Ela pode transformar campos de negócio, mas não deve
# fabricar nem descartar a identidade da origem.
SILVER_LINEAGE_COLUMNS = BRONZE_METADATA_COLUMNS

SILVER_TIMESTAMP = pa.timestamp("us")
SILVER_UTC_TIMESTAMP = pa.timestamp(
    "us",
    tz="UTC",
)


TELEMETRY_SCHEMA = pa.schema(
    [
        pa.field("event_date", pa.string()),
        pa.field("server_timestamp", SILVER_TIMESTAMP),
        pa.field("device_timestamp", SILVER_TIMESTAMP),
        pa.field("event_timestamp", SILVER_TIMESTAMP),
        pa.field("log_type", pa.string()),
        pa.field("message_type", pa.string()),
        pa.field("report_type", pa.int32()),
        pa.field("protocol_version", pa.string()),
        pa.field("device_serial", pa.string()),
        pa.field(
            "device_resolution_method",
            pa.string(),
        ),
        pa.field("terminal_status", pa.string()),
        pa.field("battery_voltage", pa.float64()),
        pa.field("location_status", pa.string()),
        pa.field("latitude", pa.float64()),
        pa.field("longitude", pa.float64()),
        pa.field("speed", pa.float64()),
        pa.field("direction_degrees", pa.float64()),
        pa.field("internal_battery", pa.float64()),
        pa.field("odometer_trip", pa.float64()),
        pa.field("odometer_total", pa.float64()),
        pa.field("horimeter", pa.float64()),
        pa.field("hdop", pa.float64()),
        pa.field("mcc", pa.string()),
        pa.field("mnc", pa.string()),
        pa.field("lac", pa.string()),
        pa.field("cell_id", pa.string()),
        pa.field("rx_level", pa.float64()),
        pa.field("serial_count", pa.int64()),
        pa.field("transmission_technology", pa.string()),
        pa.field("message_group", pa.string()),
        pa.field("io_status", pa.string()),
        pa.field("driver_id", pa.string()),
        pa.field("passenger_id", pa.string()),
        pa.field("rpm", pa.float64()),
        pa.field("tachograph_speed", pa.float64()),
        pa.field("tachograph_odometer", pa.float64()),
        pa.field("temperature_1", pa.float64()),
        pa.field("temperature_2", pa.float64()),
        pa.field("temperature_3", pa.float64()),
        pa.field("temperature_4", pa.float64()),
        pa.field("source_file", pa.string()),
        pa.field("source_file_hash", pa.string()),
        pa.field("source_row_number", pa.int64()),
        pa.field("row_id", pa.string()),
        pa.field("batch_id", pa.string()),
        pa.field("ingested_at", SILVER_UTC_TIMESTAMP),
        pa.field("ingestion_date", pa.date32()),
        pa.field("has_valid_coordinates", pa.bool_()),
        pa.field("position_quality", pa.string()),
    ]
)


DEVICE_IDENTITY_SCHEMA = pa.schema(
    [
        pa.field("event_date", pa.string()),
        pa.field("server_timestamp", SILVER_TIMESTAMP),
        pa.field("device_timestamp", SILVER_TIMESTAMP),
        pa.field("event_timestamp", SILVER_TIMESTAMP),
        pa.field("message_type", pa.string()),
        pa.field("report_type", pa.int32()),
        pa.field("protocol_version", pa.string()),
        pa.field("device_serial_raw", pa.string()),
        pa.field("device_serial", pa.string()),
        pa.field(
            "device_resolution_method",
            pa.string(),
        ),
        pa.field("iccid", pa.string()),
        pa.field("identity_auxiliary", pa.string()),
        pa.field("imsi", pa.string()),
        pa.field("imei", pa.string()),
        pa.field("source_file", pa.string()),
        pa.field("source_file_hash", pa.string()),
        pa.field("source_row_number", pa.int64()),
        pa.field("row_id", pa.string()),
        pa.field("batch_id", pa.string()),
        pa.field("ingested_at", SILVER_UTC_TIMESTAMP),
        pa.field("ingestion_date", pa.date32()),
        pa.field("has_valid_iccid_format", pa.bool_()),
        pa.field("has_valid_imsi_format", pa.bool_()),
        pa.field("has_valid_imei_format", pa.bool_()),
    ]
)

REJECTED_TEXT_COLUMNS = (
    "log_type",
    "message_type",
    "report_type_raw",
    "protocol_version",
    "device_serial_raw",
    "terminal_status",
    "battery_voltage_raw",
    "location_status_raw",
    "latitude_raw",
    "longitude_raw",
    "speed_raw",
    "direction_raw",
    "internal_battery_raw",
    "odometer_trip_raw",
    "odometer_total_raw",
    "horimeter_raw",
    "hdop_raw",
    "mcc",
    "mnc",
    "lac",
    "cell_id",
    "rx_level_raw",
    "serial_count_raw",
    "transmission_technology",
    "message_group",
    "io_status",
    "driver_id",
    "passenger_id",
    "rpm_raw",
    "tachograph_speed_raw",
    "tachograph_odometer_raw",
    "temperature_1_raw",
    "temperature_2_raw",
    "temperature_3_raw",
    "temperature_4_raw",
)


REJECTED_LOGS_SCHEMA = pa.schema(
    [
        pa.field(
            "rejection_date",
            pa.string(),
        ),
        pa.field(
            "server_timestamp",
            SILVER_TIMESTAMP,
        ),
        pa.field(
            "device_timestamp",
            SILVER_TIMESTAMP,
        ),
        *[pa.field(column, pa.string()) for column in REJECTED_TEXT_COLUMNS],
        pa.field(
            "device_serial",
            pa.string(),
        ),
        pa.field(
            "device_resolution_method",
            pa.string(),
        ),
        pa.field("source_file", pa.string()),
        pa.field("source_file_hash", pa.string()),
        pa.field("source_row_number", pa.int64()),
        pa.field("row_id", pa.string()),
        pa.field("batch_id", pa.string()),
        pa.field("ingested_at", SILVER_UTC_TIMESTAMP),
        pa.field("ingestion_date", pa.date32()),
        pa.field(
            "event_timestamp",
            SILVER_TIMESTAMP,
        ),
        pa.field(
            "rejection_reason",
            pa.string(),
        ),
    ]
)
