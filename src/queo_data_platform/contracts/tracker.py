# Nome lógico da tabela Bronze que armazenará
# os logs recebidos dos rastreadores.
BRONZE_TABLE_NAME = "tracker_logs"


# Colunas mínimas que um arquivo de tracker precisa possuir
# para ser aceito pela Bronze.
#
# Colunas adicionais são permitidas.
#
# Essas colunas pertencem à fonte:
# a plataforma valida sua existência, mas não as cria.
RAW_TRACKER_REQUIRED_COLUMNS = (
    "DATA_SERVIDOR",
    "TM_STAMP",
    "TIPO_LOG",
    "MESS_TYPE",
    "REPT_TYPE",
    "PRT_VER",
    "S/N ou IMEI",
    "TERM_STATUS",
    "BAT_VOLT",
    "LOC_STATUS",
    "LAT",
    "LONT",
    "SPEED",
    "DIR",
    "INT_BATT",
    "ODO_TRIP",
    "ODO_TOTAL",
    "HORIMETER",
    "HDOP",
    "MCC",
    "MNC",
    "LAC",
    "CELL_ID",
    "RX_LEVEL",
    "SER_COUNT",
    "TX_TECH",
    "GRP_MSG",
    "IO_STATUS",
    "DRIVER_ID",
    "PASS_ID",
    "RPM",
    "TACHO_SPD",
    "TACHO_ODO",
    "TEMP_1",
    "TEMP_2",
    "TEMP_3",
    "TEMP_4",
)


# Metadados técnicos adicionados exclusivamente
# pela própria plataforma durante a ingestão.
BRONZE_METADATA_COLUMNS = (
    "source_file",
    "source_file_hash",
    "source_row_number",
    "row_id",
    "batch_id",
    "ingested_at",
    "ingestion_date",
)


# Conjunto mínimo de colunas garantidas por um
# registro Bronze depois da ingestão.
#
# Podem existir outras colunas provenientes da fonte.
BRONZE_REQUIRED_COLUMNS = RAW_TRACKER_REQUIRED_COLUMNS + BRONZE_METADATA_COLUMNS
