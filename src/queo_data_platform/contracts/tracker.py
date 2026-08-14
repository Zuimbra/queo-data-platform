# Nome lógico da tabela Bronze que armazenará os logs dos rastreadores.
BRONZE_TABLE_NAME = "tracker_logs"


# Colunas que devem existir no arquivo recebido da fonte.
#
# Essas colunas pertencem ao dado original.
# A plataforma não as cria; ela apenas valida se estão presentes.
RAW_TRACKER_COLUMNS = (
    "DATA_SERVIDOR",
    "TM_STAMP",
    "NR_SEQ",
    "NR_DISPOSITIVO",
    "DS_MSG",
    "LAT",
    "LON",
    "NR_SAT",
    "VEL",
    "IGN",
    "ODOM",
    "HORIM",
    "ENTRADA",
    "SAIDA",
    "NR_GSM",
    "NR_GPS",
    "NR_CEL",
    "NR_MSG",
    "DS_TIPO",
    "NR_SERIE",
)


# Metadados técnicos adicionados pela própria plataforma durante a ingestão.
#
# Eles permitem rastrear de onde cada registro veio e em qual execução
# ele entrou no Lakehouse.
BRONZE_METADATA_COLUMNS = (
    "source_file",
    "source_file_hash",
    "source_row_number",
    "row_id",
    "batch_id",
    "ingested_at",
    "ingestion_date",
)


# Representa o contrato lógico completo de uma linha Bronze.
#
# dados da fonte
# +
# metadados técnicos
# =
# registro Bronze
BRONZE_COLUMNS = RAW_TRACKER_COLUMNS + BRONZE_METADATA_COLUMNS