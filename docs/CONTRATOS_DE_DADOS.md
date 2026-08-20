# Contratos de Dados — QUEO Data Platform

# 1. Objetivo

Este documento descreve os contratos de dados produzidos e consumidos pela QUEO Data Platform.

O objetivo é responder:

```text
quais tabelas existem?

qual é a finalidade de cada tabela?

qual é a granularidade?

qual é a chave lógica?

como a tabela é particionada?

de onde os dados vêm?

quais campos existem?

o que cada campo significa?

quais campos são derivados?

quais campos preservam lineage?

qual camada pode consumir cada produto?
```

A arquitetura de dados atual é:

```text
CSV
 ↓
Raw
 ↓
Bronze
 ↓
Silver
 ↓
Gold
 ↓
Query Layer
 ↓
REST API
```

---

# 2. Visão geral dos contratos

```text
data/
│
├── raw/
│
└── lakehouse/
    │
    ├── 00_control/
    │   └── ingestion_files
    │
    ├── 01_bronze/
    │   └── tracker_logs
    │
    ├── 02_silver/
    │   ├── telemetry_events
    │   ├── device_identity_events
    │   └── rejected_logs
    │
    └── 03_gold/
        ├── dim_device
        ├── device_last_position
        ├── device_route_points
        ├── device_daily_summary
        └── data_quality_summary
```

Resumo:

| Camada | Produto | Granularidade |
|---|---|---|
| Control | `ingestion_files` | um evento de estado da ingestão |
| Bronze | `tracker_logs` | uma linha física do arquivo de origem |
| Silver | `telemetry_events` | um evento de telemetria aceito |
| Silver | `device_identity_events` | um evento T1 de identidade aceito |
| Silver | `rejected_logs` | um registro rejeitado pela classificação |
| Gold | `dim_device` | um dispositivo |
| Gold | `device_last_position` | no máximo uma posição por dispositivo |
| Gold | `device_route_points` | um ponto de rota |
| Gold | `device_daily_summary` | um dispositivo em um dia |
| Gold | `data_quality_summary` | uma data de processamento lógico |

---

# 3. Tipos utilizados neste documento

Os schemas Silver e Gold são definidos em PyArrow.

Os tipos apresentados abaixo seguem esta nomenclatura:

```text
string
→ texto

int32
→ inteiro de 32 bits

int64
→ inteiro de 64 bits

float64
→ número decimal de dupla precisão

bool
→ verdadeiro/falso

date32
→ data

timestamp
→ timestamp sem timezone explícito

timestamp[UTC]
→ timestamp normalizado em UTC
```

---

# 4. Contrato da fonte CSV

Antes da Bronze existir uma tabela persistida, existe o contrato estrutural da fonte.

O arquivo de tracker precisa possuir, no mínimo:

```text
DATA_SERVIDOR
TM_STAMP
TIPO_LOG
MESS_TYPE
REPT_TYPE
PRT_VER
S/N ou IMEI
TERM_STATUS
BAT_VOLT
LOC_STATUS
LAT
LONT
SPEED
DIR
INT_BATT
ODO_TRIP
ODO_TOTAL
HORIMETER
HDOP
MCC
MNC
LAC
CELL_ID
RX_LEVEL
SER_COUNT
TX_TECH
GRP_MSG
IO_STATUS
DRIVER_ID
PASS_ID
RPM
TACHO_SPD
TACHO_ODO
TEMP_1
TEMP_2
TEMP_3
TEMP_4
```

Essas são:

```text
RAW_TRACKER_REQUIRED_COLUMNS
```

Colunas adicionais são permitidas.

Portanto o contrato é:

```text
campos mínimos obrigatórios
+
campos adicionais opcionais
```

---

# 5. Semântica dos campos da fonte

## Tempo

### `DATA_SERVIDOR`

Timestamp registrado pelo servidor.

Na Silver torna-se:

```text
server_timestamp
```

### `TM_STAMP`

Timestamp informado pelo equipamento.

Na Silver torna-se:

```text
device_timestamp
```

---

## Classificação

### `TIPO_LOG`

Tipo de log original.

Na Silver:

```text
log_type
```

### `MESS_TYPE`

Tipo de mensagem do protocolo.

Exemplos:

```text
T1
T2
T3
T14
```

Na Silver:

```text
message_type
```

### `REPT_TYPE`

Tipo de relatório.

Na Silver é convertido para:

```text
report_type
```

### `PRT_VER`

Versão do protocolo.

Na Silver:

```text
protocol_version
```

---

## Identidade

### `S/N ou IMEI`

Campo original utilizado como serial ou identificador do dispositivo.

Na Silver é inicialmente preservado como:

```text
device_serial_raw
```

e posteriormente pode originar:

```text
device_serial
```

---

## Posição e movimento

```text
LAT
LONT
SPEED
DIR
HDOP
```

tornam-se:

```text
latitude
longitude
speed
direction_degrees
hdop
```

---

## Estado e energia

```text
TERM_STATUS
BAT_VOLT
LOC_STATUS
INT_BATT
```

possuem interpretação dependente do tipo de mensagem.

Para telemetria, por exemplo:

```text
BAT_VOLT
→ battery_voltage
```

Enquanto em T1:

```text
BAT_VOLT
→ iccid
```

Essa diferença ocorre porque T1 possui semântica de identidade.

---

# 6. Área de controle

# `00_control/ingestion_files`

## Finalidade

Registrar o histórico operacional da ingestão Bronze.

A tabela é:

```text
append-only
```

Uma mudança de estado não modifica a linha anterior.

Ela produz:

```text
novo evento
```

---

## Granularidade

```text
1 linha
=
1 evento de controle de ingestão
```

Um mesmo:

```text
batch_id
```

pode possuir mais de uma linha.

Exemplo:

```text
PROCESSING
↓
SUCCESS
```

---

## Chave física/lógica

Cada evento possui:

```text
control_event_id
```

gerado individualmente.

`batch_id` identifica a tentativa de ingestão, mas não é único na tabela porque a mesma tentativa pode produzir diferentes eventos de estado.

---

## Particionamento

Atualmente:

```text
sem particionamento explícito
```

---

## Schema

| Campo | Tipo | Obrigatório | Significado |
|---|---|---:|---|
| `control_event_id` | string | sim | identificador único do evento de controle |
| `batch_id` | string | sim | identificador da tentativa de ingestão |
| `source_file` | string | sim | nome do arquivo processado |
| `source_file_hash` | string | não | SHA-256 do arquivo |
| `status` | string | sim | estado da ingestão |
| `stage` | string | sim | estágio responsável pelo evento |
| `started_at` | timestamp[UTC] | sim | início da tentativa |
| `finished_at` | timestamp[UTC] | não | conclusão da tentativa |
| `row_count` | int64 | não | linhas recebidas |
| `inserted_row_count` | int64 | não | linhas efetivamente inseridas |
| `duplicate_row_count` | int64 | não | linhas ignoradas por duplicidade |
| `status_reason` | string | não | razão estruturada do status |
| `error_message` | string | não | mensagem técnica de erro |
| `recorded_at` | timestamp[UTC] | sim | instante de gravação do evento |

---

# 7. Estados da tabela de controle

Valores atuais de:

```text
status
```

são:

```text
PROCESSING
SUCCESS
FAILED
SKIPPED
```

---

## `PROCESSING`

Representa:

```text
tentativa iniciada
```

---

## `SUCCESS`

Representa:

```text
ingestão concluída
```

Somente hashes com:

```text
SUCCESS
```

são considerados processados com sucesso para fins de idempotência de arquivo.

---

## `FAILED`

Representa falha em etapas como:

```text
hash
validação
persistência Bronze
```

---

## `SKIPPED`

Representa um arquivo cujo conteúdo já havia sido processado com sucesso.

---

# 8. `stage`

Atualmente:

```text
stage = BRONZE
```

A coluna existe para deixar o contrato preparado para histórico de eventos de outras etapas, embora hoje o controle seja utilizado na ingestão Bronze.

---

# 9. `status_reason`

Razões atualmente utilizadas incluem:

```text
FILE_HASH_ERROR

SOURCE_FILE_HASH_ALREADY_SUCCESSFUL

VALIDATION_FAILED

BRONZE_WRITE_FAILED
```

`status_reason` deve ser utilizado para classificação programática.

`error_message` pode conter informação textual mais detalhada.

---

# 10. Bronze

# `01_bronze/tracker_logs`

## Finalidade

Preservar os registros recebidos da fonte junto com lineage técnico suficiente para:

```text
auditoria
idempotência
reprocessamento
rastreabilidade
incrementalidade
```

---

## Granularidade

```text
1 linha Bronze
=
1 linha física do arquivo CSV
```

---

## Chave técnica

```text
row_id
```

É calculado deterministicamente a partir de:

```text
source_file_hash
+
source_row_number
```

---

## Particionamento

```text
ingestion_date
```

Importante:

```text
ingestion_date
```

representa quando a plataforma ingeriu o dado.

Não representa necessariamente:

```text
data do evento
```

---

# 11. Natureza do schema Bronze

A Bronze não possui um schema PyArrow rígido equivalente aos contratos Silver e Gold.

Seu contrato é:

```text
RAW_TRACKER_REQUIRED_COLUMNS
+
BRONZE_METADATA_COLUMNS
```

A fonte pode adicionar outras colunas.

Essas colunas podem ser preservadas pela Bronze através da evolução do schema Delta.

Por isso:

```text
Bronze
→ contrato mínimo extensível
```

enquanto:

```text
Silver / Gold
→ schemas explícitos
```

---

# 12. Tipagem Bronze

Os campos da fonte são lidos inicialmente como:

```text
texto
```

A Bronze evita converter semanticamente campos de negócio.

A tipagem real ocorre na Silver.

Isso significa que valores como:

```text
"12.4"
"2026-08-20 10:00:00"
"T2"
```

continuam conceitualmente próximos da representação original durante a ingestão.

---

# 13. Metadados Bronze

A plataforma acrescenta:

```text
source_file
source_file_hash
source_row_number
row_id
batch_id
ingested_at
ingestion_date
```

---

## `source_file`

Nome do arquivo de origem.

Exemplo:

```text
logs_rastreador_2026-08-20.csv
```

---

## `source_file_hash`

SHA-256 do conteúdo completo do arquivo.

É utilizado para:

```text
idempotência de arquivo
```

---

## `source_row_number`

Posição da linha de dados dentro do arquivo.

Começa em:

```text
1
```

---

## `row_id`

Identificador determinístico da linha.

Conceitualmente:

```text
SHA256(
    source_file_hash
    +
    source_row_number
)
```

---

## `batch_id`

Identificador da tentativa de ingestão que inseriu a linha.

---

## `ingested_at`

Timestamp UTC da ingestão.

---

## `ingestion_date`

Data derivada de:

```text
ingested_at
```

e utilizada como partição Bronze.

---

# 14. Contrato de lineage

A Silver deve preservar a linhagem produzida pela Bronze.

O conjunto comum é:

```text
source_file
source_file_hash
source_row_number
row_id
batch_id
ingested_at
ingestion_date
```

Esses campos permitem percorrer conceitualmente:

```text
registro Silver
        ↓
linha Bronze
        ↓
arquivo original
```

---

# 15. Silver

A Silver possui três contratos explícitos:

```text
telemetry_events

device_identity_events

rejected_logs
```

---

# 16. Timestamps Silver

Existem três conceitos temporais principais.

## `server_timestamp`

Timestamp informado pelo servidor.

---

## `device_timestamp`

Timestamp informado pelo equipamento.

---

## `event_timestamp`

Timestamp canônico do evento.

Regra:

```text
device_timestamp
        ↓
quando válido
```

caso contrário:

```text
server_timestamp
```

---

## `event_date`

Representação:

```text
YYYY-MM-DD
```

derivada de:

```text
event_timestamp
```

É utilizada como partição dos produtos Silver aceitos.

---

# 17. Identidade canônica Silver

A Silver diferencia:

```text
device_serial_raw
```

de:

```text
device_serial
```

---

## `device_serial_raw`

Valor recebido originalmente da fonte.

É preservado principalmente em produtos nos quais essa evidência é necessária.

---

## `device_serial`

Identidade canônica utilizada pelo sistema.

---

## `device_resolution_method`

Método pelo qual `device_serial` foi obtido.

Valores atuais:

```text
DIRECT
LEGACY_IMEI
UNRESOLVED
```

---

# 18. `telemetry_events`

## Finalidade

Armazenar eventos aceitos como telemetria.

---

## Origem

```text
Bronze
 ↓
normalização
 ↓
resolução de identidade
 ↓
classificação
 ↓
message_type T<n>, exceto T1
```

---

## Granularidade

```text
1 linha
=
1 evento de telemetria Silver aceito
```

---

## Particionamento

```text
event_date
```

---

## Chave de rastreabilidade

```text
row_id
```

permite retornar à linha Bronze.

A Silver não afirma que `row_id` seja a chave de evento de negócio da Gold.

---

# 19. Schema de `telemetry_events`

## Tempo e classificação

| Campo | Tipo | Significado |
|---|---|---|
| `event_date` | string | data lógica do evento |
| `server_timestamp` | timestamp | timestamp do servidor |
| `device_timestamp` | timestamp | timestamp do equipamento |
| `event_timestamp` | timestamp | timestamp canônico |
| `log_type` | string | tipo original de log |
| `message_type` | string | tipo T<n> |
| `report_type` | int32 | tipo de relatório convertido |
| `protocol_version` | string | versão do protocolo |

---

## Identidade

| Campo | Tipo | Significado |
|---|---|---|
| `device_serial` | string | serial canônico |
| `device_resolution_method` | string | método de resolução |

---

## Estado e posição

| Campo | Tipo | Significado |
|---|---|---|
| `terminal_status` | string | estado reportado pelo terminal |
| `battery_voltage` | float64 | tensão de bateria |
| `location_status` | string | estado original de localização |
| `latitude` | float64 | latitude convertida |
| `longitude` | float64 | longitude convertida |
| `speed` | float64 | velocidade |
| `direction_degrees` | float64 | direção |
| `internal_battery` | float64 | bateria interna |
| `odometer_trip` | float64 | odômetro da viagem |
| `odometer_total` | float64 | odômetro acumulado |
| `horimeter` | float64 | horímetro |
| `hdop` | float64 | medida HDOP |

---

## Rede e comunicação

| Campo | Tipo | Significado |
|---|---|---|
| `mcc` | string | Mobile Country Code recebido |
| `mnc` | string | Mobile Network Code recebido |
| `lac` | string | Location Area Code |
| `cell_id` | string | identificador da célula |
| `rx_level` | float64 | nível de recepção |
| `serial_count` | int64 | contador serial da mensagem |
| `transmission_technology` | string | tecnologia de transmissão |
| `message_group` | string | grupo da mensagem |

---

## IO, motorista e passageiros

| Campo | Tipo |
|---|---|
| `io_status` | string |
| `driver_id` | string |
| `passenger_id` | string |

---

## Telemetria complementar

| Campo | Tipo |
|---|---|
| `rpm` | float64 |
| `tachograph_speed` | float64 |
| `tachograph_odometer` | float64 |
| `temperature_1` | float64 |
| `temperature_2` | float64 |
| `temperature_3` | float64 |
| `temperature_4` | float64 |

---

## Lineage

| Campo | Tipo |
|---|---|
| `source_file` | string |
| `source_file_hash` | string |
| `source_row_number` | int64 |
| `row_id` | string |
| `batch_id` | string |
| `ingested_at` | timestamp[UTC] |
| `ingestion_date` | date32 |

---

## Qualidade de posição

| Campo | Tipo | Significado |
|---|---|---|
| `has_valid_coordinates` | bool | coordenadas estão dentro da faixa geográfica aceita |
| `position_quality` | string | classificação de qualidade da posição |

Valores atuais de:

```text
position_quality
```

incluem:

```text
VALID

MISSING_COORDINATES

INVALID_COORDINATES

LOW_GPS_PRECISION
```

---

# 20. `device_identity_events`

## Finalidade

Armazenar eventos:

```text
T1
```

aceitos como eventos de identidade.

---

## Granularidade

```text
1 linha
=
1 evento T1 aceito
```

---

## Particionamento

```text
event_date
```

---

# 21. Schema de `device_identity_events`

## Tempo

| Campo | Tipo |
|---|---|
| `event_date` | string |
| `server_timestamp` | timestamp |
| `device_timestamp` | timestamp |
| `event_timestamp` | timestamp |

---

## Protocolo

| Campo | Tipo |
|---|---|
| `message_type` | string |
| `report_type` | int32 |
| `protocol_version` | string |

---

## Identidade

| Campo | Tipo | Significado |
|---|---|---|
| `device_serial_raw` | string | serial original recebido |
| `device_serial` | string | serial canônico |
| `device_resolution_method` | string | método de resolução |
| `iccid` | string | ICCID extraído da T1 |
| `identity_auxiliary` | string | campo auxiliar de identidade |
| `imsi` | string | IMSI extraído da T1 |
| `imei` | string | IMEI extraído da T1 |

---

# 22. Mapeamento específico da T1

Na interpretação atual:

```text
BAT_VOLT
→ iccid
```

```text
LOC_STATUS
→ identity_auxiliary
```

```text
LAT
→ imsi
```

```text
LONT
→ imei
```

Essa semântica é específica do produto de identidade.

Ela não altera a interpretação dos mesmos campos quando a mensagem representa telemetria.

---

# 23. Lineage de `device_identity_events`

| Campo | Tipo |
|---|---|
| `source_file` | string |
| `source_file_hash` | string |
| `source_row_number` | int64 |
| `row_id` | string |
| `batch_id` | string |
| `ingested_at` | timestamp[UTC] |
| `ingestion_date` | date32 |

---

# 24. Indicadores de formato de identidade

| Campo | Tipo | Regra |
|---|---|---|
| `has_valid_iccid_format` | bool | ICCID possui 18–22 dígitos |
| `has_valid_imsi_format` | bool | IMSI possui 14–16 dígitos |
| `has_valid_imei_format` | bool | IMEI possui exatamente 15 dígitos |

Esses campos medem:

```text
formato
```

e não necessariamente validade cadastral externa.

---

# 25. `rejected_logs`

## Finalidade

Preservar registros que chegaram até a Silver, mas não cumpriram os requisitos necessários para:

```text
telemetry_events
```

ou:

```text
device_identity_events
```

---

## Granularidade

```text
1 linha
=
1 linha Bronze rejeitada
```

---

## Particionamento

```text
rejection_date
```

---

# 26. `rejection_date`

Quando existe:

```text
event_timestamp
```

a data deriva dele.

Quando nenhum timestamp válido existe:

```text
rejection_date = "unknown"
```

Isso permite persistir e medir registros sem referência temporal válida.

---

# 27. Motivos de rejeição

Valores atuais produzidos pela classificação incluem:

```text
MISSING_MESSAGE_TYPE

INVALID_MESSAGE_TYPE

MISSING_OR_INVALID_TIMESTAMP

MISSING_DEVICE_SERIAL
```

O contrato Gold também possui suporte para contabilizar:

```text
UNKNOWN_REJECTION_REASON
```

quando presente.

---

# 28. Schema de `rejected_logs`

## Controle da rejeição

| Campo | Tipo |
|---|---|
| `rejection_date` | string |
| `server_timestamp` | timestamp |
| `device_timestamp` | timestamp |

---

## Campos de origem normalizados como texto

Os seguintes campos são preservados principalmente como texto:

```text
log_type
message_type
report_type_raw
protocol_version
device_serial_raw
terminal_status
battery_voltage_raw
location_status_raw
latitude_raw
longitude_raw
speed_raw
direction_raw
internal_battery_raw
odometer_trip_raw
odometer_total_raw
horimeter_raw
hdop_raw
mcc
mnc
lac
cell_id
rx_level_raw
serial_count_raw
transmission_technology
message_group
io_status
driver_id
passenger_id
rpm_raw
tachograph_speed_raw
tachograph_odometer_raw
temperature_1_raw
temperature_2_raw
temperature_3_raw
temperature_4_raw
```

Todos são:

```text
string
```

no contrato de rejeição.

Isso evita perder a evidência original por falha de conversão.

---

## Identidade resolvida

| Campo | Tipo |
|---|---|
| `device_serial` | string |
| `device_resolution_method` | string |

Mesmo uma linha rejeitada pode possuir identidade resolvida.

---

## Lineage

| Campo | Tipo |
|---|---|
| `source_file` | string |
| `source_file_hash` | string |
| `source_row_number` | int64 |
| `row_id` | string |
| `batch_id` | string |
| `ingested_at` | timestamp[UTC] |
| `ingestion_date` | date32 |

---

## Resultado da classificação

| Campo | Tipo |
|---|---|
| `event_timestamp` | timestamp |
| `rejection_reason` | string |

---

# 29. Gold

A Gold possui cinco produtos formais:

```text
dim_device

device_last_position

device_route_points

device_daily_summary

data_quality_summary
```

Os schemas são explícitos.

Diferentemente da Bronze, a Gold não permite evolução arbitrária de campos de origem.

Ela representa produtos definidos para consumo.

---

# 30. Dois tipos de produto Gold

A Gold diferencia:

```text
entity tables
```

e:

```text
partitioned tables
```

---

## Entity tables

```text
dim_device
device_last_position
```

Possuem:

```text
device_serial
```

como chave de entidade.

---

## Partitioned tables

```text
device_route_points
→ event_date

device_daily_summary
→ event_date

data_quality_summary
→ metric_date
```

---

# 31. Base deduplicada Gold

Os principais produtos operacionais utilizam bases deduplicadas de:

```text
telemetry_events
```

e:

```text
device_identity_events
```

A deduplicação de telemetria considera:

```text
device_serial
event_timestamp
message_type
serial_count
latitude
longitude
speed
```

A de identidade considera:

```text
device_serial
event_timestamp
imei
imsi
iccid
```

---

# 32. Exceção: qualidade

```text
data_quality_summary
```

não utiliza as views deduplicadas.

Ele mede diretamente o resultado da Silver:

```text
telemetry aceito
+
identity aceito
+
rejected
```

Isso é importante para interpretar suas contagens.

---

# 33. `dim_device`

## Finalidade

Representar a visão consolidada de cada dispositivo conhecido pela plataforma.

---

## Granularidade

```text
1 linha
=
1 device_serial
```

---

## Chave

```text
device_serial
```

---

## Particionamento

```text
sem particionamento por data
```

---

## Origem

```text
device_identity_events
+
telemetry_events
```

através das bases Gold deduplicadas.

---

# 34. Schema de `dim_device`

## Identificação

| Campo | Tipo | Significado |
|---|---|---|
| `device_serial` | string | chave canônica do dispositivo |
| `current_imei` | string | IMEI do evento de identidade mais recente |
| `current_imsi` | string | IMSI mais recente |
| `current_iccid` | string | ICCID mais recente |
| `current_identity_auxiliary` | string | informação auxiliar mais recente |
| `current_protocol_version` | string | versão atual de protocolo inferida das atividades mais recentes |

---

## Histórico temporal

| Campo | Tipo |
|---|---|
| `first_seen_at` | timestamp |
| `last_seen_at` | timestamp |
| `first_identity_at` | timestamp |
| `last_identity_at` | timestamp |
| `first_telemetry_at` | timestamp |
| `last_telemetry_at` | timestamp |

---

## Contagens

| Campo | Tipo |
|---|---|
| `identity_event_count` | int64 |
| `telemetry_event_count` | int64 |

---

## Indicadores de existência

| Campo | Tipo |
|---|---|
| `has_identity_event` | bool |
| `has_telemetry_event` | bool |

---

## Qualidade da identidade atual

| Campo | Tipo |
|---|---|
| `current_imei_format_valid` | bool |
| `current_imsi_format_valid` | bool |
| `current_iccid_format_valid` | bool |

---

# 35. Semântica de `first_seen_at` e `last_seen_at`

Esses campos consideram:

```text
identidade
+
telemetria
```

Portanto:

```text
first_seen_at
```

não significa necessariamente:

```text
primeira telemetria
```

e:

```text
last_seen_at
```

não significa necessariamente:

```text
última posição
```

São medidas de atividade geral conhecida do dispositivo.

---

# 36. `device_last_position`

## Finalidade

Publicar a posição mais recente considerada utilizável para cada dispositivo.

---

## Granularidade

```text
0 ou 1 linha por device_serial
```

Um dispositivo conhecido pode não aparecer se nunca possuir posição publicável.

---

## Chave

```text
device_serial
```

---

## Particionamento

```text
sem particionamento
```

---

## Origem

```text
telemetry_events
```

através da base Gold deduplicada.

---

# 37. Critérios da última posição

Para participar:

```text
has_valid_coordinates = TRUE
```

e:

```text
latitude != 0
OU
longitude != 0
```

Ou seja:

```text
(0,0)
```

é excluído.

---

# 38. Critério de ordenação

Prioridade:

```text
1. event_timestamp DESC
2. server_timestamp DESC NULLS LAST
3. serial_count DESC NULLS LAST
```

O primeiro registro desse ranking é publicado.

---

# 39. Schema de `device_last_position`

| Campo | Tipo | Significado |
|---|---|---|
| `device_serial` | string | dispositivo |
| `last_position_date` | string | data da última posição |
| `last_position_at` | timestamp | instante lógico da posição |
| `received_at` | timestamp | instante registrado pelo servidor |
| `latitude` | float64 | latitude |
| `longitude` | float64 | longitude |
| `speed` | float64 | velocidade |
| `direction_degrees` | float64 | direção |
| `battery_voltage` | float64 | tensão de bateria |
| `internal_battery` | float64 | bateria interna |
| `odometer_total` | float64 | odômetro acumulado |
| `horimeter` | float64 | horímetro |
| `hdop` | float64 | precisão GPS reportada |
| `rx_level` | float64 | nível de recepção |
| `message_type` | string | tipo da mensagem |
| `report_type` | int32 | tipo do relatório |
| `serial_count` | int64 | contador serial |
| `protocol_version` | string | versão do protocolo |
| `position_quality` | string | qualidade da posição |
| `source_file` | string | arquivo de origem |

---

# 40. `device_route_points`

## Finalidade

Publicar a trajetória histórica ordenada de cada dispositivo.

---

## Granularidade

```text
1 linha
=
1 ponto de rota
```

---

## Chave lógica

```text
event_date
+
device_serial
+
point_sequence
```

---

## Particionamento

```text
event_date
```

---

## Origem

```text
telemetry_events
```

através da base Gold deduplicada.

---

# 41. `point_sequence`

A sequência é calculada por:

```text
device_serial
+
event_date
```

e ordenada por:

```text
event_timestamp
received_at
serial_count
```

Assim:

```text
point_sequence = 1
```

representa o primeiro ponto do dispositivo naquele dia.

---

# 42. `is_moving`

Regra atual:

```text
speed >= 5
→ TRUE
```

Caso contrário:

```text
FALSE
```

`NULL` é tratado como zero para esse indicador específico.

---

# 43. Schema de `device_route_points`

| Campo | Tipo |
|---|---|
| `event_date` | string |
| `device_serial` | string |
| `point_sequence` | int64 |
| `event_timestamp` | timestamp |
| `received_at` | timestamp |
| `latitude` | float64 |
| `longitude` | float64 |
| `speed` | float64 |
| `direction_degrees` | float64 |
| `odometer_trip` | float64 |
| `odometer_total` | float64 |
| `horimeter` | float64 |
| `hdop` | float64 |
| `rx_level` | float64 |
| `message_type` | string |
| `report_type` | int32 |
| `serial_count` | int64 |
| `protocol_version` | string |
| `position_quality` | string |
| `is_moving` | bool |
| `source_file` | string |

---

# 44. `device_daily_summary`

## Finalidade

Consolidar a atividade de um dispositivo durante um dia.

---

## Granularidade

```text
1 linha
=
1 device_serial
+
1 event_date
```

---

## Chave lógica

```text
event_date
+
device_serial
```

---

## Particionamento

```text
event_date
```

---

## Origem

```text
telemetry_events
```

através da base Gold deduplicada.

---

# 45. Schema de `device_daily_summary`

## Identificação e janela

| Campo | Tipo |
|---|---|
| `event_date` | string |
| `device_serial` | string |
| `first_event_at` | timestamp |
| `last_event_at` | timestamp |

---

## Volume

| Campo | Tipo | Significado |
|---|---|---|
| `message_count` | int64 | eventos de telemetria no dia |
| `distinct_message_type_count` | int64 | quantidade de tipos de mensagem distintos |

---

## Posição

| Campo | Tipo |
|---|---|
| `valid_position_count` | int64 |
| `invalid_position_count` | int64 |
| `low_gps_precision_count` | int64 |
| `valid_position_percentage` | float64 |

A porcentagem é:

```text
valid_position_count
--------------------
message_count
× 100
```

---

# 46. Movimento e velocidade

| Campo | Tipo |
|---|---|
| `moving_event_count` | int64 |
| `stopped_event_count` | int64 |
| `average_speed` | float64 |
| `average_speed_while_moving` | float64 |
| `maximum_speed` | float64 |

Movimento:

```text
speed >= 5
```

Parada:

```text
speed IS NOT NULL
AND speed < 5
```

---

# 47. HDOP diário

| Campo | Tipo |
|---|---|
| `average_hdop` | float64 |
| `minimum_hdop` | float64 |
| `maximum_hdop` | float64 |

---

# 48. Bateria principal

| Campo | Tipo |
|---|---|
| `minimum_battery_voltage` | float64 |
| `maximum_battery_voltage` | float64 |
| `average_battery_voltage` | float64 |

---

# 49. Bateria interna

| Campo | Tipo |
|---|---|
| `minimum_internal_battery` | float64 |
| `maximum_internal_battery` | float64 |
| `average_internal_battery` | float64 |

---

# 50. Odômetro

| Campo | Tipo |
|---|---|
| `first_odometer_total` | float64 |
| `last_odometer_total` | float64 |
| `odometer_delta_raw` | float64 |
| `has_odometer_regression` | bool |

Quando:

```text
last_odometer_total
<
first_odometer_total
```

o resultado é:

```text
odometer_delta_raw = NULL
```

e:

```text
has_odometer_regression = TRUE
```

---

# 51. Primeira e última posição válida do dia

| Campo | Tipo |
|---|---|
| `first_valid_position_at` | timestamp |
| `last_valid_position_at` | timestamp |
| `first_latitude` | float64 |
| `first_longitude` | float64 |
| `last_latitude` | float64 |
| `last_longitude` | float64 |

---

# 52. Observação sobre `(0,0)`

O resumo diário utiliza:

```text
has_valid_coordinates
```

produzido pela Silver.

Como:

```text
0
```

está dentro das faixas válidas de latitude e longitude:

```text
(0,0)
```

pode ser contabilizado em:

```text
valid_position_count
```

no contrato atual.

Entretanto:

```text
device_route_points
device_last_position
```

excluem explicitamente `(0,0)`.

Essa diferença faz parte da semântica atual e não deve ser ignorada por consumidores.

---

# 53. `data_quality_summary`

## Finalidade

Medir a qualidade do processamento Silver por data.

---

## Granularidade

```text
1 linha
=
1 metric_date
```

---

## Chave lógica

```text
metric_date
```

---

## Particionamento

```text
metric_date
```

---

## Origem

Diretamente de:

```text
telemetry_events
device_identity_events
rejected_logs
```

---

# 54. Schema de `data_quality_summary`

| Campo | Tipo | Significado |
|---|---|---|
| `metric_date` | string | data lógica da métrica |
| `telemetry_event_count` | int64 | telemetrias aceitas |
| `identity_event_count` | int64 | identidades aceitas |
| `accepted_event_count` | int64 | total aceito |
| `rejected_event_count` | int64 | total rejeitado |
| `total_event_count` | int64 | aceitos + rejeitados |
| `rejection_percentage` | float64 | percentual de rejeição |
| `missing_message_type_count` | int64 | rejeições por mensagem ausente |
| `invalid_message_type_count` | int64 | rejeições por tipo inválido |
| `invalid_timestamp_count` | int64 | rejeições por timestamp |
| `missing_device_serial_count` | int64 | rejeições por identidade |
| `unknown_rejection_count` | int64 | rejeições classificadas como desconhecidas |

---

# 55. Fórmulas de qualidade

```text
accepted_event_count
=
telemetry_event_count
+
identity_event_count
```

```text
total_event_count
=
accepted_event_count
+
rejected_event_count
```

```text
rejection_percentage
=
rejected_event_count
--------------------
total_event_count
× 100
```

O percentual é arredondado para:

```text
4 casas decimais
```

---

# 56. `metric_date = unknown`

Registros rejeitados que não possuem timestamp válido podem produzir:

```text
rejection_date = unknown
```

Consequentemente:

```text
metric_date = unknown
```

pode existir em:

```text
data_quality_summary
```

Isso não representa uma data cronológica.

Representa:

```text
registros cuja data não pôde ser determinada
```

---

# 57. Relações entre produtos

A cadeia principal é:

```text
tracker_logs
     ↓
     ├────────→ telemetry_events
     │
     ├────────→ device_identity_events
     │
     └────────→ rejected_logs
```

Depois:

```text
telemetry_events
      │
      ├──→ dim_device
      ├──→ device_last_position
      ├──→ device_route_points
      └──→ device_daily_summary
```

```text
device_identity_events
      │
      └──→ dim_device
```

E:

```text
telemetry_events
+
device_identity_events
+
rejected_logs
        ↓
data_quality_summary
```

---

# 58. Mapa de lineage

Na Bronze:

```text
source_file
source_file_hash
source_row_number
row_id
batch_id
ingested_at
ingestion_date
```

A Silver preserva esse lineage.

Isso permite:

```text
telemetry_events.row_id
        ↓
tracker_logs.row_id
        ↓
source_file
+
source_row_number
```

O mesmo vale para:

```text
device_identity_events
rejected_logs
```

---

# 59. Lineage na Gold

Nem todos os produtos Gold preservam todo o lineage Bronze.

Isso é intencional.

Produtos agregados como:

```text
dim_device
device_daily_summary
data_quality_summary
```

representam múltiplos eventos e, portanto, não possuem uma única linha de origem.

Já produtos orientados a evento podem preservar elementos selecionados, por exemplo:

```text
device_last_position.source_file
```

e:

```text
device_route_points.source_file
```

A Gold deve preservar lineage somente quando ele possui interpretação inequívoca para o produto.

---

# 60. Chaves e granularidades consolidadas

| Produto | Chave / granularidade |
|---|---|
| `ingestion_files` | `control_event_id` |
| `tracker_logs` | `row_id` |
| `telemetry_events` | evento Silver rastreável por `row_id` |
| `device_identity_events` | evento Silver rastreável por `row_id` |
| `rejected_logs` | registro rejeitado rastreável por `row_id` |
| `dim_device` | `device_serial` |
| `device_last_position` | `device_serial` |
| `device_route_points` | `event_date + device_serial + point_sequence` |
| `device_daily_summary` | `event_date + device_serial` |
| `data_quality_summary` | `metric_date` |

---

# 61. Particionamento consolidado

| Produto | Partição |
|---|---|
| `ingestion_files` | nenhuma |
| `tracker_logs` | `ingestion_date` |
| `telemetry_events` | `event_date` |
| `device_identity_events` | `event_date` |
| `rejected_logs` | `rejection_date` |
| `dim_device` | nenhuma |
| `device_last_position` | nenhuma |
| `device_route_points` | `event_date` |
| `device_daily_summary` | `event_date` |
| `data_quality_summary` | `metric_date` |

---

# 62. Três conceitos de data

A plataforma possui três conceitos temporais diferentes.

## `ingestion_date`

```text
quando o dado entrou na plataforma
```

Usado na Bronze.

---

## `event_date`

```text
quando o evento aconteceu
```

Derivado de:

```text
event_timestamp
```

Usado nos produtos de evento Silver e Gold.

---

## `rejection_date`

```text
data possível de atribuir ao registro rejeitado
```

Pode ser:

```text
unknown
```

---

## `metric_date`

```text
data utilizada para agregação de qualidade
```

Pode derivar tanto de:

```text
event_date
```

quanto:

```text
rejection_date
```

---

# 63. Semântica de NULL

A plataforma utiliza `NULL` deliberadamente para representar:

```text
valor ausente
valor não fornecido
valor impossível de converter
valor não aplicável
```

Exemplo:

```text
speed_raw = "ABC"
```

pode resultar em:

```text
speed = NULL
```

sem rejeitar necessariamente todo o evento.

---

# 64. NULL não significa zero

Consumidores não devem interpretar automaticamente:

```text
NULL
```

como:

```text
0
```

Exemplo:

```text
speed = NULL
```

significa:

```text
velocidade não disponível
```

e não necessariamente:

```text
veículo parado
```

---

# 65. Indicadores booleanos

Quando o sistema precisa distinguir qualidade ou condição, utiliza campos explícitos.

Exemplos:

```text
has_valid_coordinates

has_valid_imei_format

has_odometer_regression

has_identity_event

has_telemetry_event

is_moving
```

Consumidores devem preferir esses indicadores em vez de tentar reconstruir a mesma regra independentemente.

---

# 66. Contratos e evolução de schema

A estratégia difere por camada.

## Bronze

Permite:

```text
schema extensível
```

porque precisa preservar campos adicionais da fonte.

---

## Silver

Utiliza:

```text
schemas explícitos
```

porque representa produtos operacionais interpretados.

---

## Gold

Utiliza:

```text
schemas explícitos
```

porque representa contratos voltados a consumo.

---

# 67. Compatibilidade Silver

A execução incremental exige que existam:

```text
telemetry_events
device_identity_events
rejected_logs
```

com as colunas necessárias do contrato atual.

Se não:

```text
incremental não é considerado seguro
```

e o sistema executa:

```text
FULL de recuperação
```

---

# 68. Compatibilidade Gold

A execução incremental exige a existência de:

```text
dim_device
device_last_position
device_route_points
device_daily_summary
data_quality_summary
```

Quando o conjunto está incompleto:

```text
Gold FULL
```

é utilizado para recuperar o estado.

---

# 69. Contrato interno da Query Layer

A Query Layer não cria um novo produto persistido.

Ela oferece uma interface de leitura sobre a Gold.

Seu contrato principal é:

```text
QueryService
```

e, para paginação:

```text
QueryPage
```

---

# 70. `QueryPage`

Possui:

```text
items
total
limit
offset
returned
has_more
next_offset
```

Semântica:

```text
items
→ registros da página

total
→ registros que atendem ao filtro antes da paginação

returned
→ tamanho da página retornada

has_more
→ existem outros registros

next_offset
→ próximo offset ou NULL
```

---

# 71. Limites de consulta

Atualmente:

```text
DEFAULT_QUERY_LIMIT = 100
```

e:

```text
MAX_QUERY_LIMIT = 1000
```

Esses limites fazem parte do contrato de consumo da Query Layer e da API.

---

# 72. Contrato externo

Consumidores externos devem preferir:

```text
REST API
```

em vez de acessar diretamente:

```text
Delta Tables
```

A fronteira é:

```text
Consumidor
    ↓
REST API
    ↓
QueryService
    ↓
Gold
```

Os detalhes específicos de endpoints e respostas HTTP são documentados separadamente em:

```text
docs/API.md
```

---

# 73. MCP externo

Quando um serviço MCP separado consumir a plataforma, seu contrato recomendado é:

```text
MCP
 ↓
HTTP / JSON
 ↓
REST API
```

Ele não deve depender de:

```text
schemas físicos Delta
paths do Lakehouse
DuckDB
PyArrow
```

Isso mantém o contrato entre serviços independente da implementação física da plataforma.

---

# 74. Fonte de verdade dos schemas

Para contratos Silver:

```text
src/queo_data_platform/contracts/silver.py
```

Para contratos Gold:

```text
src/queo_data_platform/contracts/gold.py
```

Para o contrato mínimo Bronze:

```text
src/queo_data_platform/contracts/tracker.py
```

Para a tabela de controle:

```text
src/queo_data_platform/bronze/control.py
```

Este documento descreve esses contratos.

O código continua sendo a definição executável utilizada pela plataforma.

---

# 75. Regra para alterações futuras

Uma alteração de schema deve responder explicitamente:

```text
qual produto mudou?

a granularidade mudou?

a chave lógica mudou?

a partição mudou?

o campo é obrigatório?

o campo pode ser NULL?

a regra é retrocompatível?

o incremental continua seguro?

é necessário FULL?

a Query Layer precisa mudar?

a API pública precisa mudar?
```

Uma mudança de contrato não deve ser tratada como simples alteração de coluna.

Ela pode afetar:

```text
persistência
incrementalidade
testes
Query Layer
API
consumidores externos
```

---

# 76. Checklist de novo produto

Antes de adicionar um novo produto Silver ou Gold, definir:

```text
nome da tabela

finalidade

origem

granularidade

chave lógica

schema

tipos

campos nullable

particionamento

lineage

estratégia FULL

estratégia INCREMENTAL

consumidores

testes
```

---

# 77. Resumo

A evolução dos contratos segue:

```text
Fonte
 ↓
contrato estrutural
 ↓
Bronze
dados preservados + lineage
 ↓
Silver
contratos tipados e interpretados
 ↓
Gold
contratos analíticos
 ↓
Query Layer
contrato de consulta
 ↓
REST API
contrato externo
```

O princípio central é:

```text
quanto mais o dado avança no Lakehouse,
mais explícito e estável deve ser seu contrato
```

A Bronze privilegia:

```text
preservação
```

A Silver privilegia:

```text
semântica e qualidade
```

A Gold privilegia:

```text
consumo e estabilidade
```

E a REST API protege os consumidores externos dos detalhes físicos das tabelas internas.