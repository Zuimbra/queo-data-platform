# Operação — QUEO Data Platform

# 1. Objetivo

Este documento descreve como instalar, executar, validar, diagnosticar e recuperar a QUEO Data Platform.

Ele funciona como um runbook operacional.

O objetivo é responder perguntas como:

```text
como preparar o ambiente?

onde colocar os arquivos?

como executar o pipeline?

como saber se houve dados novos?

como executar a API?

como configurar outro diretório de dados?

como configurar CORS?

como verificar Bronze, Silver e Gold?

como investigar rejeições?

como investigar quarantine?

quando executar FULL?

como executar um rebuild?

como validar o sistema antes de um commit?
```

A arquitetura operacional é:

```text
CSV
 ↓
raw/inbox
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

# 2. Pré-requisitos

O projeto utiliza:

```text
Python >= 3.14
uv
Delta Lake
DuckDB
PyArrow
Pandas
FastAPI
Uvicorn
```

O gerenciamento de ambiente e dependências é feito por:

```text
uv
```

---

# 3. Diretório de trabalho

Todos os comandos deste documento devem ser executados na raiz do projeto.

Exemplo:

```powershell
cd C:\caminho\para\queo-data-platform
```

A raiz deve conter arquivos como:

```text
pyproject.toml
uv.lock
src/
tests/
docs/
```

---

# 4. Preparar o ambiente

Depois de clonar o projeto:

```powershell
uv sync
```

Esse comando cria ou atualiza:

```text
.venv/
```

e instala as dependências definidas em:

```text
pyproject.toml
uv.lock
```

---

# 5. Validar instalação

Execute:

```powershell
uv run python --version
```

Depois:

```powershell
uv run queo-data-platform
```

Se ainda não existirem dados e o inbox estiver vazio, o pipeline pode retornar:

```text
Bronze sem novos arquivos
Silver NOOP
Gold NOOP
```

Esse comportamento é válido.

---

# 6. Estrutura operacional de dados

Por padrão:

```text
data/
│
├── raw/
│   ├── inbox/
│   ├── archive/
│   └── quarantine/
│
└── lakehouse/
    │
    ├── 00_control/
    ├── 01_bronze/
    ├── 02_silver/
    └── 03_gold/
```

---

# 7. `raw/inbox`

É o local de entrada dos arquivos.

Arquivos CSV novos devem ser colocados em:

```text
data/raw/inbox/
```

Exemplo:

```text
data/raw/inbox/logs_rastreador_2026-08-20.csv
```

O pipeline descobre os arquivos durante a execução.

---

# 8. `raw/archive`

Arquivos processados com sucesso são movidos para:

```text
archive/
```

Arquivos cujo conteúdo já havia sido processado anteriormente também são arquivados.

Portanto:

```text
archive
```

pode conter tanto:

```text
SUCCESS
```

quanto:

```text
SKIPPED
```

---

# 9. `raw/quarantine`

Arquivos que não puderam ser processados com segurança são enviados para:

```text
quarantine/
```

Exemplos:

```text
schema inválido
erro de leitura
erro no hash
erro de persistência
```

Um arquivo em quarantine não deve ser apagado automaticamente.

Ele deve ser investigado.

---

# 10. Executar o pipeline completo

O comando principal é:

```powershell
uv run queo-data-platform
```

Também é possível executar:

```powershell
uv run python -m queo_data_platform
```

Os dois comandos executam:

```text
Bronze
 ↓
Silver
 ↓
Gold
```

---

# 11. Saída da CLI

A saída possui três blocos.

Exemplo conceitual:

```text
[PIPELINE] Execution completed

[BRONZE]
  discovered_files=1
  successful_files=1
  skipped_files=0
  failed_files=0
  inserted_rows=100
  duplicate_rows=0
  propagated_batches=1

[SILVER]
  mode=INCREMENTAL
  telemetry_rows=...
  identity_rows=...
  rejected_rows=...
  affected_event_dates=...
  affected_rejection_dates=...

[GOLD]
  mode=INCREMENTAL
  affected_devices=...
  dim_device_rows=...
  last_position_rows=...
  route_points_rows=...
  daily_summary_rows=...
  quality_summary_rows=...

[PIPELINE] has_new_data=True
[PIPELINE] has_changes=True
```

---

# 12. Interpretar a Bronze

## `discovered_files`

Quantidade de arquivos encontrados no inbox.

---

## `successful_files`

Arquivos processados com sucesso.

---

## `skipped_files`

Arquivos cujo conteúdo já havia sido processado anteriormente.

---

## `failed_files`

Arquivos que falharam e foram enviados para quarantine.

---

## `inserted_rows`

Linhas realmente novas inseridas na Bronze.

---

## `duplicate_rows`

Linhas ignoradas por:

```text
row_id
```

já existente.

---

## `propagated_batches`

Quantidade de batches propagados para a Silver.

Somente batches que inseriram linhas novas são propagados.

---

# 13. Interpretar a Silver

O campo:

```text
mode
```

pode ser:

```text
FULL
INCREMENTAL
NOOP
```

---

## `FULL`

Significa:

```text
rebuild completo
```

Pode ocorrer por:

```text
execução explícita
Silver ausente
Silver incompleta
schema incompatível
```

---

## `INCREMENTAL`

Significa:

```text
novos batches
        ↓
datas afetadas
        ↓
partições reconstruídas
```

---

## `NOOP`

Significa:

```text
nenhuma alteração Silver necessária
```

---

# 14. Interpretar a Gold

A Gold também pode executar:

```text
FULL
INCREMENTAL
NOOP
```

Um:

```text
Silver FULL
```

provoca:

```text
Gold FULL
```

quando passado ao fluxo normal.

Uma:

```text
Silver NOOP
```

com Gold completa normalmente resulta em:

```text
Gold NOOP
```

---

# 15. `has_new_data`

```text
has_new_data=True
```

significa:

```text
Bronze inseriu pelo menos uma nova linha
```

---

# 16. `has_changes`

```text
has_changes=True
```

é mais amplo.

Pode significar:

```text
nova Bronze
```

ou:

```text
rebuild Silver
```

ou:

```text
rebuild Gold
```

Portanto:

```text
has_new_data=False
has_changes=True
```

é possível.

---

# 17. Execução ociosa esperada

Quando:

```text
inbox vazio
```

e as camadas estão completas:

```text
Bronze
inserted_rows=0
        ↓
Silver
NOOP
        ↓
Gold
NOOP
```

Resultado:

```text
has_new_data=False
has_changes=False
```

Isso é comportamento normal.

---

# 18. Configurar diretório externo de dados

Por padrão:

```text
<project_root>/data
```

é utilizado.

Para alterar:

```powershell
$env:QUEO_DATA_DIR="D:\queo-data"
```

Depois execute normalmente:

```powershell
uv run queo-data-platform
```

A estrutura será resolvida abaixo de:

```text
D:\queo-data
```

---

# 19. Verificar `QUEO_DATA_DIR`

Execute:

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; print(settings.data_dir)"
```

Também é possível verificar todas as camadas:

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; print('RAW:', settings.raw_dir); print('BRONZE:', settings.bronze_dir); print('SILVER:', settings.silver_dir); print('GOLD:', settings.gold_dir)"
```

---

# 20. Remover `QUEO_DATA_DIR`

Na sessão PowerShell atual:

```powershell
Remove-Item Env:QUEO_DATA_DIR
```

Depois disso o projeto volta a utilizar:

```text
<project_root>/data
```

---

# 21. Executar somente Bronze manualmente

Para diagnóstico:

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from queo_data_platform.bronze.service import load_bronze; print(load_bronze(settings))"
```

Isso não executa Silver ou Gold.

Use apenas quando houver motivo operacional para isolar a ingestão.

---

# 22. Executar Silver FULL manualmente

Quando for necessário reconstruir toda a Silver:

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from queo_data_platform.silver.service import load_silver; print(load_silver(settings, batch_ids=None))"
```

A semântica é:

```text
batch_ids=None
→ FULL explícito
```

---

# 23. Quando usar Silver FULL

Casos típicos:

```text
mudança de regra de classificação

mudança de normalização

mudança de resolução de identidade

mudança relevante de schema Silver

necessidade de reprocessar o histórico completo
```

Não use FULL apenas porque:

```text
não chegaram arquivos novos
```

Isso deve produzir:

```text
NOOP
```

---

# 24. Executar Gold FULL manualmente

Depois de reconstruir Silver, pode ser necessário reconstruir a Gold.

Execute:

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from queo_data_platform.gold.service import load_gold; print(load_gold(settings))"
```

Sem `SilverLoadResult` explícito:

```text
Gold
→ FULL
```

---

# 25. Rebuild histórico completo recomendado

Quando uma mudança Silver altera o significado do histórico:

```text
Bronze
permanece preservada
        ↓
Silver FULL
        ↓
Gold FULL
```

Execute:

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from queo_data_platform.silver.service import load_silver; print(load_silver(settings, batch_ids=None))"
```

Depois:

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from queo_data_platform.gold.service import load_gold; print(load_gold(settings))"
```

---

# 26. Não apagar Bronze para fazer rebuild

Em condições normais, não é necessário remover:

```text
01_bronze/tracker_logs
```

para recalcular Silver ou Gold.

A Bronze é a base histórica preservada.

O fluxo correto é:

```text
Bronze existente
 ↓
Silver FULL
 ↓
Gold FULL
```

---

# 27. Verificar tabelas Delta existentes

Use:

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from deltalake import DeltaTable; from pathlib import Path; paths=[settings.control_dir/'ingestion_files', settings.bronze_dir/'tracker_logs', settings.silver_dir/'telemetry_events', settings.silver_dir/'device_identity_events', settings.silver_dir/'rejected_logs', settings.gold_dir/'dim_device', settings.gold_dir/'device_last_position', settings.gold_dir/'device_route_points', settings.gold_dir/'device_daily_summary', settings.gold_dir/'data_quality_summary']; [print(path, 'OK' if Path(path/'_delta_log').exists() else 'MISSING') for path in paths]"
```

---

# 28. Verificar quantidade de linhas de uma tabela

Exemplo Bronze:

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from deltalake import DeltaTable; print(len(DeltaTable(str(settings.bronze_dir/'tracker_logs')).to_pandas()))"
```

Silver:

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from deltalake import DeltaTable; print('telemetry:', len(DeltaTable(str(settings.silver_dir/'telemetry_events')).to_pandas())); print('identity:', len(DeltaTable(str(settings.silver_dir/'device_identity_events')).to_pandas())); print('rejected:', len(DeltaTable(str(settings.silver_dir/'rejected_logs')).to_pandas()))"
```

Gold:

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from deltalake import DeltaTable; tables=['dim_device','device_last_position','device_route_points','device_daily_summary','data_quality_summary']; [print(name, len(DeltaTable(str(settings.gold_dir/name)).to_pandas())) for name in tables]"
```

---

# 29. Verificar tabela de controle

Para visualizar eventos de ingestão:

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from deltalake import DeltaTable; df=DeltaTable(str(settings.control_dir/'ingestion_files')).to_pandas(); print(df.sort_values('recorded_at').to_string(index=False))"
```

---

# 30. Ver últimas tentativas de ingestão

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from deltalake import DeltaTable; df=DeltaTable(str(settings.control_dir/'ingestion_files')).to_pandas(); print(df.sort_values('recorded_at', ascending=False).head(20).to_string(index=False))"
```

---

# 31. Investigar somente falhas

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from deltalake import DeltaTable; df=DeltaTable(str(settings.control_dir/'ingestion_files')).to_pandas(); failed=df[df['status']=='FAILED']; print(failed[['source_file','batch_id','status_reason','error_message','recorded_at']].sort_values('recorded_at', ascending=False).to_string(index=False))"
```

---

# 32. Investigar arquivos em quarantine

Primeiro liste:

```powershell
Get-ChildItem data/raw/quarantine
```

Se `QUEO_DATA_DIR` estiver configurado:

```powershell
Get-ChildItem "$env:QUEO_DATA_DIR\raw\quarantine"
```

Depois consulte a tabela de controle para encontrar:

```text
status_reason
error_message
```

do arquivo.

---

# 33. Procedimento para arquivo em quarantine

Fluxo recomendado:

```text
arquivo em quarantine
        ↓
consultar ingestion_files
        ↓
identificar status_reason
        ↓
inspecionar arquivo
        ↓
corrigir origem ou parser
        ↓
somente depois recolocar no inbox
```

Não mova automaticamente o arquivo de volta para:

```text
inbox
```

sem entender a causa.

---

# 34. Arquivo com schema legado

Se um arquivo possuir:

```text
header diferente do contrato canônico
```

a regra atual é:

```text
validation failure
        ↓
quarantine
```

Não altere a Bronze para aceitar silenciosamente qualquer estrutura.

Se o formato legado for realmente necessário:

```text
criar parser/adaptador explícito
```

é preferível a:

```text
enfraquecer o contrato canônico
```

---

# 35. Investigar rejeições Silver

Para contar por motivo:

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from deltalake import DeltaTable; df=DeltaTable(str(settings.silver_dir/'rejected_logs')).to_pandas(); print(df['rejection_reason'].value_counts(dropna=False).to_string())"
```

---

# 36. Investigar rejeições por protocolo

Exemplo:

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from deltalake import DeltaTable; df=DeltaTable(str(settings.silver_dir/'rejected_logs')).to_pandas(); print(df.groupby(['rejection_reason','protocol_version'], dropna=False).size().sort_values(ascending=False).to_string())"
```

---

# 37. Investigar `MISSING_DEVICE_SERIAL`

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from deltalake import DeltaTable; df=DeltaTable(str(settings.silver_dir/'rejected_logs')).to_pandas(); x=df[df['rejection_reason']=='MISSING_DEVICE_SERIAL']; print(x.groupby(['protocol_version','device_resolution_method'], dropna=False).size().sort_values(ascending=False).to_string())"
```

---

# 38. Investigar métodos de resolução

Telemetria:

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from deltalake import DeltaTable; df=DeltaTable(str(settings.silver_dir/'telemetry_events')).to_pandas(); print(df['device_resolution_method'].value_counts(dropna=False).to_string())"
```

Identidade:

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from deltalake import DeltaTable; df=DeltaTable(str(settings.silver_dir/'device_identity_events')).to_pandas(); print(df['device_resolution_method'].value_counts(dropna=False).to_string())"
```

---

# 39. Investigar qualidade diária

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from deltalake import DeltaTable; df=DeltaTable(str(settings.gold_dir/'data_quality_summary')).to_pandas(); print(df.sort_values('metric_date').to_string(index=False))"
```

---

# 40. Ver maiores percentuais de rejeição

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from deltalake import DeltaTable; df=DeltaTable(str(settings.gold_dir/'data_quality_summary')).to_pandas(); print(df.sort_values('rejection_percentage', ascending=False).head(20).to_string(index=False))"
```

---

# 41. Consultar dispositivos conhecidos

Diretamente pela Query Layer:

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from queo_data_platform.query import QueryService; service=QueryService.from_settings(settings); print(service.list_devices(limit=20).to_string(index=False))"
```

---

# 42. Consultar dispositivo específico

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from queo_data_platform.query import QueryService; service=QueryService.from_settings(settings); print(service.get_device('202527000021P').to_string(index=False))"
```

Substitua:

```text
202527000021P
```

pelo serial desejado.

---

# 43. Consultar última posição pela Query Layer

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from queo_data_platform.query import QueryService; service=QueryService.from_settings(settings); print(service.get_last_position('202527000021P').to_string(index=False))"
```

---

# 44. Consultar rota

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from queo_data_platform.query import QueryService; service=QueryService.from_settings(settings); print(service.list_route_points('202527000021P', start_date='2026-08-01', end_date='2026-08-20', limit=100).to_string(index=False))"
```

---

# 45. Executar a REST API

Execute:

```powershell
uv run uvicorn queo_data_platform.api.app:app --reload
```

Por padrão:

```text
http://127.0.0.1:8000
```

---

# 46. Health check

Em outro terminal:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/health"
```

Esperado:

```text
status
------
ok
```

Esse health check confirma:

```text
processo HTTP ativo
```

Não confirma necessariamente que todas as tabelas Gold existem.

---

# 47. Swagger UI

Com a API rodando:

```text
http://127.0.0.1:8000/docs
```

---

# 48. OpenAPI

Schema:

```text
http://127.0.0.1:8000/openapi.json
```

---

# 49. Consultar dispositivos pela API

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/devices?limit=5" | ConvertTo-Json -Depth 6
```

---

# 50. Consultar dispositivo pela API

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/devices/202527000021P" | ConvertTo-Json -Depth 6
```

---

# 51. Consultar última posição pela API

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/devices/202527000021P/last-position" | ConvertTo-Json -Depth 6
```

---

# 52. Consultar rota pela API

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/devices/202527000021P/route?start_date=2026-08-01&end_date=2026-08-20&limit=100" | ConvertTo-Json -Depth 6
```

---

# 53. Consultar resumo diário

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/daily-summaries?device_serial=202527000021P&limit=10" | ConvertTo-Json -Depth 6
```

---

# 54. Consultar qualidade

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/data-quality?limit=10" | ConvertTo-Json -Depth 6
```

---

# 55. Configurar CORS

Por padrão:

```text
nenhuma origem é explicitamente permitida
```

Para desenvolvimento local:

```powershell
$env:QUEO_API_CORS_ORIGINS="http://localhost:5173"
```

Depois:

```powershell
uv run uvicorn queo_data_platform.api.app:app --reload
```

---

# 56. Múltiplas origens CORS

```powershell
$env:QUEO_API_CORS_ORIGINS="http://localhost:5173,https://app.example.com"
```

---

# 57. Remover configuração CORS

```powershell
Remove-Item Env:QUEO_API_CORS_ORIGINS
```

---

# 58. Não usar `*` como configuração padrão

A política operacional recomendada é:

```text
permitir somente origens necessárias
```

e não:

```text
liberar qualquer origem
```

---

# 59. Erros comuns da API

## 404

Exemplo:

```text
device inexistente
```

ou:

```text
última posição inexistente
```

---

## 422

Exemplo:

```text
start_date > end_date
```

ou parâmetro fora do contrato.

---

## 503

Exemplo:

```text
produto Gold ainda não existe
```

Resposta pública:

```json
{
    "detail": "Gold data is not available."
}
```

---

# 60. Diagnóstico de 503

Se a API retornar:

```text
503
```

verifique primeiro a Gold.

Exemplo:

```powershell
uv run python -c "from queo_data_platform.config.settings import settings; from pathlib import Path; [print(p.name, (p/'_delta_log').exists()) for p in settings.gold_dir.iterdir() if p.is_dir()]"
```

Se algum produto necessário estiver ausente:

```text
Gold incompleta
```

pode ser necessário executar:

```text
Gold FULL
```

---

# 61. Diagnóstico de resultado vazio

Um endpoint retornar:

```text
items = []
```

não significa necessariamente erro.

Verifique:

```text
device_serial correto?

intervalo de data correto?

produto Gold possui dados?

limite/offset corretos?
```

---

# 62. Diagnóstico de incremental inesperado

Se:

```text
INCREMENTAL
```

afetou uma data antiga, isso pode ser:

```text
late-arriving data
```

Verifique:

```text
affected_event_dates
```

e compare com o conteúdo do novo batch.

---

# 63. Diagnóstico de FULL inesperado na Silver

Possíveis causas:

```text
batch_ids=None
```

ou:

```text
uma tabela Silver não existe
```

ou:

```text
schema Silver incompatível
```

O FULL de recuperação é comportamento deliberado.

---

# 64. Diagnóstico de FULL inesperado na Gold

Possíveis causas:

```text
silver_result=None
```

```text
Silver.mode=FULL
```

```text
uma das cinco tabelas Gold não existe
```

---

# 65. Não forçar incremental em estado incompleto

Quando:

```text
Silver incompleta
```

ou:

```text
Gold incompleta
```

o sistema prefere:

```text
FULL
```

Isso deve ser preservado.

Executar incremental sobre estado incompleto poderia deixar produtos inconsistentes.

---

# 66. Backup antes de alterações destrutivas

Antes de:

```text
apagar uma camada
alterar manualmente Delta
mover grandes volumes
executar experimentos destrutivos
```

faça uma cópia do diretório de dados ou trabalhe em:

```text
QUEO_DATA_DIR
```

separado.

Exemplo:

```powershell
$env:QUEO_DATA_DIR="C:\temp\queo-data-test"
```

---

# 67. Preferir rebuild a edição manual de Delta

Não altere manualmente registros em:

```text
Silver
Gold
```

para corrigir regra de negócio.

O procedimento recomendado é:

```text
corrigir código
        ↓
testar
        ↓
rebuild
```

Isso mantém:

```text
reprodutibilidade
auditabilidade
```

---

# 68. Quality gate

Antes de considerar um bloco concluído:

```powershell
uv run ruff format .
uv run ruff check .
uv run pyright
uv run pytest
```

---

# 69. Testes unitários

```powershell
uv run pytest tests/unit -v
```

---

# 70. Testes de integração

```powershell
uv run pytest tests/integration -v
```

---

# 71. Testes da API

```powershell
uv run pytest tests/api -v
```

---

# 72. Testes específicos da Silver

```powershell
uv run pytest tests/unit/test_silver_identity_resolution.py -v
uv run pytest tests/unit/test_silver_classification.py -v
uv run pytest tests/unit/test_silver_transformation.py -v
uv run pytest tests/integration/test_silver_service.py -v
```

---

# 73. Testes específicos da Gold

```powershell
uv run pytest tests/unit/test_gold_*.py -v
uv run pytest tests/integration/test_gold_service.py -v
```

---

# 74. Teste completo do pipeline

```powershell
uv run pytest tests/integration/test_pipeline_service.py -v
```

---

# 75. Quando validar com dados reais

Testes automatizados devem ser executados sempre.

Mas mudanças como:

```text
nova classificação
nova regra de identidade
mudança de produto Gold
```

também podem exigir:

```text
validação sobre histórico real
```

Fluxo:

```text
unit tests
 ↓
integration tests
 ↓
full pytest
 ↓
rebuild histórico
 ↓
medir resultado
```

---

# 76. Não usar redução de rejeições como único critério

Exemplo:

```text
MISSING_DEVICE_SERIAL caiu
```

não prova sozinho que uma regra está correta.

Também deve ser verificado:

```text
quais linhas foram recuperadas?

qual método de resolução foi usado?

protocolos não elegíveis continuam protegidos?

Gold mudou de forma coerente?
```

---

# 77. Procedimento após alteração da resolução de identidade

Execute:

```powershell
uv run pytest tests/unit/test_silver_identity_resolution.py -v
```

Depois:

```powershell
uv run pytest tests/integration/test_silver_service.py -v
```

Depois:

```powershell
uv run pytest
```

Se a mudança alterar histórico:

```text
Silver FULL
 ↓
Gold FULL
```

Depois compare métricas.

---

# 78. Procedimento após alteração de schema Silver

Verifique:

```text
contracts/silver.py
```

Depois:

```powershell
uv run pyright
uv run pytest tests/unit/test_silver_contracts.py -v
uv run pytest tests/integration/test_silver_service.py -v
uv run pytest
```

A execução operacional pode entrar em:

```text
FULL de recuperação
```

se as tabelas persistidas não forem compatíveis.

---

# 79. Procedimento após alteração de schema Gold

Verifique:

```text
contracts/gold.py
```

Depois:

```powershell
uv run pytest tests/unit/test_gold_contracts.py -v
uv run pytest tests/integration/test_gold_service.py -v
uv run pytest
```

Gold incompatível deve ser reconstruída.

---

# 80. Procedimento após alteração da Query Layer

Execute:

```powershell
uv run pytest tests/unit/test_query_service.py -v
uv run pytest tests/unit/test_query_summary_service.py -v
```

Se a API depende da mudança:

```powershell
uv run pytest tests/api -v
```

Depois:

```powershell
uv run pytest
```

---

# 81. Procedimento após alteração da API

Execute:

```powershell
uv run pytest tests/api -v
```

Depois:

```powershell
uv run pyright
uv run pytest
```

E faça smoke test real:

```powershell
uv run uvicorn queo_data_platform.api.app:app --reload
```

---

# 82. Smoke test mínimo da API

Depois de iniciar Uvicorn:

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/health"
```

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/devices?limit=1" | ConvertTo-Json -Depth 6
```

```powershell
Invoke-RestMethod "http://127.0.0.1:8000/api/v1/data-quality?limit=1" | ConvertTo-Json -Depth 6
```

---

# 83. Encerrar Uvicorn

No terminal em que o servidor está rodando:

```text
Ctrl + C
```

---

# 84. Verificar status Git antes de versionar

```powershell
git status
```

Depois:

```powershell
git --no-pager diff --stat
```

---

# 85. Revisar alterações antes do commit

```powershell
git --no-pager diff
```

Depois de adicionar:

```powershell
git --no-pager diff --cached
```

ou:

```powershell
git --no-pager diff --cached --stat
```

---

# 86. Princípio de commits operacionais

Evite misturar no mesmo commit:

```text
mudança funcional
+
diagnóstico
+
documentação não relacionada
+
refactor amplo
```

Prefira commits que representem:

```text
um bloco lógico concluído
```

---

# 87. Não versionar dados operacionais

Diretórios como:

```text
data/
```

não devem ser utilizados como fonte de código.

Dados locais do Lakehouse devem permanecer separados do versionamento, salvo arquivos de exemplo explicitamente destinados ao repositório.

---

# 88. Procedimento normal diário

O fluxo operacional mais comum é:

```text
1. colocar CSV no inbox
        ↓
2. executar pipeline
        ↓
3. verificar resultado CLI
        ↓
4. se failed_files > 0:
   investigar quarantine
        ↓
5. se rejected_rows mudou significativamente:
   investigar rejected_logs
        ↓
6. consumir Gold/API
```

---

# 89. Procedimento de execução sem novos dados

```powershell
uv run queo-data-platform
```

Esperado:

```text
discovered_files=0
inserted_rows=0
propagated_batches=0

Silver mode=NOOP

Gold mode=NOOP

has_new_data=False
has_changes=False
```

---

# 90. Procedimento após novo arquivo válido

```text
arquivo
 ↓
inbox
 ↓
pipeline
```

Esperado:

```text
successful_files > 0
inserted_rows > 0
propagated_batches > 0
Silver INCREMENTAL
Gold INCREMENTAL
```

salvo quando alguma camada precisar de recovery FULL.

---

# 91. Procedimento para arquivo duplicado

Se o conteúdo já possui:

```text
SUCCESS
```

no controle:

```text
SKIPPED
```

é esperado.

O arquivo deve terminar em:

```text
archive
```

e não deve provocar novo processamento Silver.

---

# 92. Procedimento para falha de validação

Esperado:

```text
FAILED
```

com:

```text
status_reason = VALIDATION_FAILED
```

e arquivo movido para:

```text
quarantine
```

Investigue o contrato do CSV antes de qualquer mudança no código.

---

# 93. Procedimento de recuperação Silver

Se uma ou mais tabelas Silver forem:

```text
ausentes
incompletas
incompatíveis
```

não tente reconstruí-las parcialmente manualmente.

Execute:

```text
Silver FULL
```

a partir da Bronze preservada.

Depois:

```text
Gold FULL
```

---

# 94. Procedimento de recuperação Gold

Se uma das cinco tabelas Gold estiver ausente:

```text
dim_device
device_last_position
device_route_points
device_daily_summary
data_quality_summary
```

execute:

```text
Gold FULL
```

em vez de tentar recompor apenas um produto manualmente.

---

# 95. Fonte de verdade em uma recuperação

A hierarquia é:

```text
Bronze
→ fonte histórica preservada

Silver
→ derivada da Bronze

Gold
→ derivada da Silver
```

Portanto:

```text
problema Gold
→ reconstruir da Silver
```

```text
problema Silver
→ reconstruir da Bronze
```

---

# 96. Não reconstruir Bronze a partir da Silver

A relação é unidirecional:

```text
Bronze
 ↓
Silver
 ↓
Gold
```

Silver e Gold não são fontes para recriar a Bronze.

---

# 97. Integridade antes de consumo externo

Antes de disponibilizar dados para um consumidor novo, verifique:

```text
Pipeline saudável
        ↓
Gold completa
        ↓
QueryService responde
        ↓
API responde
```

O consumidor externo não deve ser utilizado para diagnosticar problemas internos de processamento.

---

# 98. Integração com MCP externo

Quando um serviço MCP externo for integrado:

```text
MCP
 ↓
REST API
 ↓
QueryService
 ↓
Gold
```

O teste operacional deve começar pela API.

Primeiro valide:

```text
endpoint HTTP
```

Depois valide:

```text
cliente do MCP
```

Por fim:

```text
MCP tool
```

Isso separa problemas da Data Platform de problemas do serviço MCP.

---

# 99. Checklist operacional rápido

Antes de declarar o sistema saudável:

```text
[ ] inbox em estado esperado

[ ] quarantine investigado

[ ] pipeline executa

[ ] Bronze sem falhas inesperadas

[ ] Silver em modo esperado

[ ] Gold em modo esperado

[ ] rejected_logs dentro do comportamento esperado

[ ] Gold completa

[ ] Query Layer responde

[ ] /health responde

[ ] endpoints principais respondem

[ ] ruff aprovado

[ ] pyright aprovado

[ ] pytest aprovado
```

---

# 100. Princípio operacional final

A regra principal de operação é:

```text
não corrigir manualmente o estado derivado
quando ele pode ser reproduzido a partir da camada anterior
```

Portanto:

```text
arquivo problemático
→ investigar fonte / Bronze

Silver problemática
→ reconstruir da Bronze

Gold problemática
→ reconstruir da Silver

consulta problemática
→ investigar Query Layer

HTTP problemático
→ investigar API
```

Essa abordagem preserva:

```text
reprodutibilidade
auditabilidade
consistência
rastreabilidade
```

e reduz a chance de criar um estado no Lakehouse que o código não consegue reproduzir.