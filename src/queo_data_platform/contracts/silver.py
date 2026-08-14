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
