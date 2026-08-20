# REST API — QUEO Data Platform

## Visão geral

A REST API é a camada HTTP de leitura da QUEO Data Platform.

Ela não consulta diretamente:

```text
Bronze
Silver
Delta Tables
DuckDB
```

O fluxo é:

```text
Gold
  ↓
Query Layer
  ↓
REST API
  ↓
consumidores externos
```

A API utiliza exclusivamente os produtos analíticos publicados na Gold por meio de:

```python
QueryService
```

Isso mantém separadas as responsabilidades de:

```text
processamento
consulta
transporte HTTP
```

---

# Execução

Na raiz do projeto:

```powershell
uv run uvicorn queo_data_platform.api.app:app --reload
```

Por padrão, a aplicação fica disponível em:

```text
http://127.0.0.1:8000
```

---

# Documentação interativa

FastAPI disponibiliza automaticamente Swagger UI em:

```text
http://127.0.0.1:8000/docs
```

E o schema OpenAPI em:

```text
http://127.0.0.1:8000/openapi.json
```

---

# Health check

```http
GET /health
```

Resposta:

```json
{
  "status": "ok"
}
```

O health check valida apenas que o processo HTTP está ativo.

Ele não exige que as Delta Tables Gold estejam disponíveis.

---

# Dispositivos

## Listar dispositivos

```http
GET /api/v1/devices
```

Parâmetros:

```text
limit
offset
```

Exemplo:

```text
/api/v1/devices?limit=100&offset=0
```

A resposta contém:

```text
items
total
limit
offset
returned
has_more
next_offset
```

---

## Consultar dispositivo

```http
GET /api/v1/devices/{device_serial}
```

Exemplo:

```text
/api/v1/devices/202527000021P
```

Se o dispositivo não existir:

```http
404 Not Found
```

---

# Última posição

```http
GET /api/v1/devices/{device_serial}/last-position
```

Exemplo:

```text
/api/v1/devices/202527000021P/last-position
```

A resposta representa o produto Gold:

```text
device_last_position
```

---

# Rota

```http
GET /api/v1/devices/{device_serial}/route
```

Filtros disponíveis:

```text
start_date
end_date
limit
offset
```

Exemplo:

```text
/api/v1/devices/202527000021P/route?start_date=2026-06-01&end_date=2026-06-03&limit=100
```

As datas utilizam:

```text
YYYY-MM-DD
```

A consulta utiliza:

```text
event_date
```

que também é a coluna de particionamento do produto Gold.

---

# Resumo diário

```http
GET /api/v1/daily-summaries
```

Filtros:

```text
device_serial
start_date
end_date
limit
offset
```

Exemplo:

```text
/api/v1/daily-summaries?device_serial=202527000021P&start_date=2026-06-01&end_date=2026-06-30
```

A origem é:

```text
device_daily_summary
```

---

# Qualidade dos dados

```http
GET /api/v1/data-quality
```

Filtros:

```text
start_date
end_date
limit
offset
```

Exemplo:

```text
/api/v1/data-quality?start_date=2026-06-01&end_date=2026-06-30
```

A origem é:

```text
data_quality_summary
```

---

# Paginação

Consultas que podem retornar múltiplos registros possuem:

```text
limit
offset
```

O limite máximo da Query Layer é:

```text
1000 registros
```

A resposta contém metadados como:

```json
{
  "total": 14732,
  "limit": 100,
  "offset": 0,
  "returned": 100,
  "has_more": true,
  "next_offset": 100
}
```

O campo:

```text
total
```

representa a quantidade total de registros que atendem aos filtros antes da aplicação de:

```text
LIMIT
OFFSET
```

---

# CORS

Por padrão:

```text
nenhuma origem é explicitamente autorizada
```

Para permitir aplicações web específicas, utilize:

```text
QUEO_API_CORS_ORIGINS
```

Exemplo PowerShell:

```powershell
$env:QUEO_API_CORS_ORIGINS="http://localhost:5173"
```

Múltiplas origens:

```powershell
$env:QUEO_API_CORS_ORIGINS="http://localhost:5173,https://app.example.com"
```

Depois execute:

```powershell
uv run uvicorn queo_data_platform.api.app:app --reload
```

Para remover a variável da sessão:

```powershell
Remove-Item Env:QUEO_API_CORS_ORIGINS
```

Não utilize:

```text
*
```

como padrão da aplicação.

A política é liberar explicitamente apenas os consumidores necessários.

---

# Diretório de dados

A API utiliza a mesma configuração da plataforma.

Por padrão:

```text
<project_root>/data
```

Pode ser substituído por:

```text
QUEO_DATA_DIR
```

Exemplo:

```powershell
$env:QUEO_DATA_DIR="D:\queo-data"
```

A Query Layer passa então a consumir:

```text
D:\queo-data\lakehouse\03_gold
```

---

# Tratamento de erros

## 404

Utilizado quando um recurso específico não existe.

Exemplo:

```text
device desconhecido
última posição inexistente
```

---

## 422

Utilizado para parâmetros semanticamente inválidos.

Exemplo:

```text
start_date > end_date
```

ou parâmetros HTTP que não respeitam o contrato esperado.

---

## 503

Utilizado quando um produto Gold necessário ainda não está disponível.

A API retorna:

```json
{
  "detail": "Gold data is not available."
}
```

Caminhos internos do Lakehouse não são expostos na resposta HTTP.

---

# Arquitetura

A separação principal é:

```text
api/routes.py
        ↓
QueryService
        ↓
Gold
```

As rotas são responsáveis por:

```text
HTTP
validação de parâmetros
status codes
serialização
modelos de resposta
```

A Query Layer é responsável por:

```text
filtros
paginação
ordenação
contagens
consultas DuckDB
acesso às Delta Tables Gold
```

Portanto não deve existir:

```text
rota FastAPI
    ↓
DeltaTable(...)
```

nem:

```text
rota FastAPI
    ↓
SQL DuckDB
```

Essas responsabilidades pertencem à Query Layer.

---

# Testes

Testes HTTP:

```powershell
uv run pytest tests/api -v
```

Testes de configuração:

```powershell
uv run pytest tests/unit/test_api_settings.py -v
```

Validação completa:

```powershell
uv run ruff check .
uv run pyright
uv run pytest
```