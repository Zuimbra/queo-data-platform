# Integração com MCP — QUEO Data Platform

# 1. Visão geral

A QUEO Data Platform foi estruturada para separar claramente:

```text
processamento
consulta
exposição
consumo
```

O fluxo principal é:

```text
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

A introdução de um serviço MCP não exige que a lógica de acesso aos dados seja reimplementada.

O MCP deve atuar como uma camada de consumo e tradução semântica para clientes compatíveis com o Model Context Protocol.

A arquitetura recomendada, quando o MCP existe em outro serviço, é:

```text
                         QUEO DATA PLATFORM

Raw
 │
 ▼
Bronze
 │
 ▼
Silver
 │
 ▼
Gold
 │
 ▼
QueryService
 │
 ▼
REST API
 │
 │ HTTP / JSON
 │
 └──────────────────────────────────┐
                                    │
                                    ▼
                              MCP SERVICE
                                    │
                                    ▼
                                MCP Tools
                                    │
                                    ▼
                              LLM / MCP Client
```

A REST API funciona, nesse cenário, como a fronteira oficial entre:

```text
Data Platform
```

e:

```text
MCP Service
```

---

# 2. Por que o MCP não precisa acessar a Gold diretamente

O serviço MCP não deve conhecer detalhes internos como:

```text
Delta Lake
DuckDB
PyArrow
estrutura de diretórios
partições
Gold paths
```

Esses detalhes pertencem à QUEO Data Platform.

Por exemplo, o MCP não deveria fazer:

```python
DeltaTable(
    "data/lakehouse/03_gold/device_last_position"
)
```

nem:

```python
duckdb.connect()
```

nem duplicar SQL como:

```sql
SELECT *
FROM device_last_position
WHERE device_serial = ?
```

O fluxo correto é:

```text
MCP Tool
   ↓
REST API
   ↓
QueryService
   ↓
Gold
```

Assim, a responsabilidade de cada componente permanece clara.

---

# 3. Responsabilidades da QUEO Data Platform

A QUEO Data Platform é responsável por:

```text
ingestão
processamento
normalização
qualidade
persistência
consultas
paginação
filtros
contratos HTTP
```

Sua arquitetura interna é:

```text
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

A plataforma conhece:

```text
Delta Lake
DuckDB
PyArrow
schemas
partições
incrementalidade
```

Consumidores externos não precisam conhecer esses detalhes.

---

# 4. Responsabilidades do serviço MCP

O serviço MCP deve ficar responsável por:

```text
definir MCP tools
descrever semanticamente as tools
receber parâmetros do cliente MCP
chamar a Data Platform
interpretar respostas HTTP
formatar respostas adequadas para o modelo
```

Exemplo:

```text
MCP tool
get_last_position
        ↓
HTTP GET
        ↓
QUEO Data Platform
        ↓
QueryService
        ↓
device_last_position
```

O serviço MCP não é responsável por descobrir como calcular a última posição.

Essa regra já pertence à Gold e à Query Layer.

---

# 5. Query Layer como fronteira interna de leitura

A Query Layer é a camada central de acesso aos produtos Gold.

Atualmente ela expõe operações como:

```python
list_devices(...)
get_device(...)
list_last_positions(...)
get_last_position(...)
list_route_points(...)
list_daily_summaries(...)
list_quality_summaries(...)
```

e versões paginadas como:

```python
page_devices(...)
page_last_positions(...)
page_route_points(...)
page_daily_summaries(...)
page_quality_summaries(...)
```

O fluxo interno é:

```text
QueryService
     ↓
DeltaTable
     ↓
PyArrow Dataset
     ↓
DuckDB
     ↓
DataFrame
```

A camada HTTP reutiliza essas operações.

Portanto:

```text
Query Layer
```

é a fonte única de verdade para leitura da Gold.

---

# 6. REST API como fronteira externa

A REST API transforma as capacidades internas do `QueryService` em contratos HTTP.

Atualmente estão disponíveis:

```text
GET /health
```

```text
GET /api/v1/devices
```

```text
GET /api/v1/devices/{device_serial}
```

```text
GET /api/v1/devices/{device_serial}/last-position
```

```text
GET /api/v1/devices/{device_serial}/route
```

```text
GET /api/v1/daily-summaries
```

```text
GET /api/v1/data-quality
```

O fluxo é:

```text
HTTP Request
     ↓
FastAPI
     ↓
QueryService
     ↓
Gold
     ↓
DataFrame
     ↓
Pydantic
     ↓
JSON
```

Essa interface é a opção natural para consumidores externos.

---

# 7. Implementação recomendada para um MCP externo

Quando o MCP está em outro serviço, a arquitetura recomendada é:

```text
┌─────────────────────────────────────┐
│ QUEO DATA PLATFORM                  │
│                                     │
│ Bronze                              │
│   ↓                                 │
│ Silver                              │
│   ↓                                 │
│ Gold                                │
│   ↓                                 │
│ QueryService                        │
│   ↓                                 │
│ REST API                            │
└───────────────────┬─────────────────┘
                    │
                    │ HTTP / JSON
                    │
┌───────────────────▼─────────────────┐
│ MCP SERVICE                         │
│                                     │
│ API Client                          │
│   ↓                                 │
│ MCP Tools                           │
│   ↓                                 │
│ MCP Server                          │
└───────────────────┬─────────────────┘
                    │
                    │ MCP
                    ▼
               LLM / Client
```

O MCP precisa conhecer apenas:

```text
URL da API
contratos dos endpoints
parâmetros
status HTTP
estrutura JSON
```

---

# 8. Exemplo — `get_last_position`

Uma tool MCP poderia possuir conceitualmente:

```python
get_last_position(
    device_serial: str
)
```

O MCP não consulta a Gold.

Ele chama:

```http
GET /api/v1/devices/{device_serial}/last-position
```

Exemplo:

```http
GET /api/v1/devices/202527000021P/last-position
```

O fluxo completo é:

```text
LLM
 ↓
MCP tool
get_last_position
 ↓
HTTP
 ↓
GET /api/v1/devices/202527000021P/last-position
 ↓
FastAPI
 ↓
QueryService.get_last_position(
    "202527000021P"
)
 ↓
device_last_position
 ↓
JSON
 ↓
MCP
 ↓
LLM
```

---

# 9. Exemplo — consulta de rota

Tool MCP:

```text
get_device_route
```

Parâmetros conceituais:

```text
device_serial
start_date
end_date
limit
offset
```

A implementação MCP chamaria:

```http
GET /api/v1/devices/202527000021P/route
```

com:

```text
start_date=2026-06-01
end_date=2026-06-03
limit=100
```

Exemplo:

```text
/api/v1/devices/202527000021P/route
    ?start_date=2026-06-01
    &end_date=2026-06-03
    &limit=100
```

A API delega para:

```python
QueryService.page_route_points(...)
```

que consulta:

```text
device_route_points
```

utilizando os filtros de:

```text
device_serial
event_date
```

---

# 10. Exemplo — resumo diário

Uma tool MCP pode ser:

```text
get_device_daily_summary
```

Ela chama:

```http
GET /api/v1/daily-summaries
```

com:

```text
device_serial
start_date
end_date
limit
offset
```

Exemplo:

```text
/api/v1/daily-summaries
    ?device_serial=202527000021P
    &start_date=2026-06-01
    &end_date=2026-06-30
```

O fluxo interno continua:

```text
REST API
   ↓
QueryService.page_daily_summaries()
   ↓
device_daily_summary
```

---

# 11. Exemplo — qualidade dos dados

Uma tool MCP pode ser:

```text
get_data_quality
```

Chamando:

```http
GET /api/v1/data-quality
```

com:

```text
start_date
end_date
limit
offset
```

Exemplo:

```text
/api/v1/data-quality
    ?start_date=2026-06-01
    &end_date=2026-06-30
```

O serviço MCP pode posteriormente transformar a resposta em uma descrição mais apropriada para o modelo.

Por exemplo:

```text
API
 ↓
dados estruturados
 ↓
MCP
 ↓
descrição semântica da ferramenta
 ↓
LLM
```

A Data Platform continua responsável pelos números.

O MCP fica responsável por tornar esses números acessíveis ao agente.

---

# 12. Paginação entre REST API e MCP

A Query Layer já fornece:

```text
total
limit
offset
returned
has_more
next_offset
```

Por exemplo:

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

O MCP pode utilizar esses campos para decidir se:

```text
retorna somente a página atual
```

ou:

```text
faz novas chamadas
```

dependendo da finalidade da tool.

É importante evitar que uma tool faça automaticamente:

```text
buscar 15 mil registros
```

sem necessidade.

Para LLMs, normalmente é preferível utilizar:

```text
filtros mais específicos
+
limites menores
```

---

# 13. Tratamento de erros no MCP

A API já representa situações por status HTTP.

## 404

Exemplo:

```text
dispositivo não existe
```

O MCP pode transformar:

```http
404
```

em algo semanticamente útil:

```text
Nenhum dispositivo com esse serial foi encontrado.
```

---

## 422

Exemplo:

```text
start_date > end_date
```

O MCP pode devolver ao cliente:

```text
O intervalo de datas informado é inválido.
```

---

## 503

Exemplo:

```text
Gold ainda não disponível
```

A API retorna:

```json
{
    "detail": "Gold data is not available."
}
```

O MCP não deve tentar abrir a Gold diretamente como fallback.

Ele deve tratar isso como indisponibilidade temporária da Data Platform.

---

# 14. Configuração do endereço da Data Platform no MCP

O serviço MCP não deve codificar:

```text
http://127.0.0.1:8000
```

diretamente nas tools.

A recomendação é utilizar uma configuração como:

```text
QUEO_DATA_PLATFORM_API_URL
```

Exemplo local:

```text
QUEO_DATA_PLATFORM_API_URL=http://127.0.0.1:8000
```

Em outro ambiente:

```text
QUEO_DATA_PLATFORM_API_URL=https://data-api.example.com
```

O código MCP pode então montar:

```text
BASE_URL
+
/api/v1/...
```

Assim:

```text
desenvolvimento
homologação
produção
```

podem utilizar endpoints diferentes sem mudança de código.

---

# 15. Cliente HTTP centralizado no serviço MCP

O MCP não deve realizar chamadas HTTP diretamente em cada tool.

Evite:

```text
tool A
→ HTTP próprio

tool B
→ HTTP próprio

tool C
→ HTTP próprio
```

O recomendado é:

```text
MCP Tools
    ↓
DataPlatformClient
    ↓
REST API
```

Exemplo conceitual:

```python
class DataPlatformClient:
    def list_devices(...):
        ...

    def get_device(...):
        ...

    def get_last_position(...):
        ...

    def get_route(...):
        ...

    def get_daily_summaries(...):
        ...

    def get_data_quality(...):
        ...
```

Depois:

```text
MCP tool
    ↓
DataPlatformClient
    ↓
REST API
```

Isso permite centralizar:

```text
base URL
timeout
headers
autenticação futura
tratamento de erros
retry futuro
logging
```

---

# 16. Escalabilidade da arquitetura

A arquitetura atual foi construída para permitir crescimento sem duplicar lógica.

Hoje:

```text
Gold
 ↓
QueryService
 ↓
REST API
```

Se surgir um novo consumidor:

```text
dashboard
serviço de analytics
MCP
aplicação mobile
backoffice
```

ele pode consumir:

```text
REST API
```

sem conhecer a implementação interna.

Exemplo:

```text
                        ┌── Dashboard
                        │
                        ├── MCP Service
REST API ────────────────┼── Backoffice
                        │
                        ├── Mobile
                        │
                        └── Integrações
```

---

# 17. Escalabilidade pela Query Layer

Também existe outra forma de expansão.

Se uma nova capacidade ainda não existe na REST API, ela deve normalmente nascer primeiro na:

```text
Query Layer
```

Exemplo:

```text
novo requisito:

listar dispositivos
sem telemetria há 7 dias
```

Não devemos começar criando:

```text
GET /api/v1/inactive-devices
```

com SQL dentro da rota.

O fluxo recomendado é:

```text
novo requisito
      ↓
QueryService
      ↓
novo método
      ↓
testes
      ↓
REST API
      ↓
consumidores externos
```

Por exemplo:

```python
QueryService.list_inactive_devices(...)
```

Depois:

```text
REST API
 ↓
GET /api/v1/devices/inactive
```

E finalmente:

```text
MCP
 ↓
list_inactive_devices
```

---

# 18. Evolução vertical de uma nova funcionalidade

Uma nova capacidade deve atravessar as camadas de forma controlada.

Exemplo:

```text
"obter última comunicação de cada dispositivo"
```

Primeiro avaliar:

```text
a Gold já possui essa informação?
```

Se sim:

```text
Gold existente
      ↓
QueryService
      ↓
REST API
      ↓
MCP
```

Se não:

```text
regra analítica
      ↓
Gold
      ↓
QueryService
      ↓
REST API
      ↓
MCP
```

Assim o MCP nunca vira o local onde regras de negócio analíticas são implementadas.

---

# 19. Quando estender diretamente a Query Layer

O acesso direto ao `QueryService` também é uma possibilidade.

Arquitetura:

```text
Gold
 ↓
QueryService
 ├── REST API
 └── consumidor interno
```

Isso é adequado quando o consumidor:

```text
faz parte do mesmo processo
faz parte do mesmo pacote Python
possui acesso ao mesmo filesystem
compartilha ciclo de deploy
```

Por exemplo:

```text
CLI interna
job administrativo
script local
teste
serviço Python dentro do mesmo deployment
```

Nesse cenário:

```python
from queo_data_platform.query import (
    QueryService,
)
```

pode ser uma solução válida.

---

# 20. Quando NÃO usar diretamente a Query Layer

Se o consumidor estiver em:

```text
outro repositório
outro container
outro servidor
outro ciclo de deploy
outra aplicação
```

não é recomendável fazer:

```text
serviço externo
      ↓
instalar queo-data-platform
      ↓
QueryService
      ↓
filesystem da Gold
```

Isso exigiria compartilhar:

```text
Lakehouse
paths
bibliotecas Delta
DuckDB
credenciais futuras
configuração interna
```

A separação entre serviços seria perdida.

Nesse cenário, prefira:

```text
HTTP
```

---

# 21. Comparação das duas estratégias

## Consumo pela REST API

```text
MCP externo
    ↓
HTTP
    ↓
REST API
    ↓
Query Layer
```

### Vantagens

```text
baixo acoplamento
deploy independente
contrato explícito
linguagem independente
não compartilha filesystem
não expõe Delta
não expõe DuckDB
mais fácil de autenticar futuramente
mais fácil de versionar
```

### Recomendado para

```text
serviço MCP separado
frontend
dashboard
mobile
integrações externas
```

---

## Consumo direto pela Query Layer

```text
consumidor interno
    ↓
QueryService
    ↓
Gold
```

### Vantagens

```text
sem overhead HTTP
reutilização direta
menos serialização
boa integração interna
```

### Desvantagens

```text
forte acoplamento Python
acesso ao filesystem
mesmas dependências
mesmo ambiente
```

### Recomendado para

```text
componentes internos
scripts
CLI
jobs
mesmo serviço
```

---

# 22. Estratégia recomendada para o MCP existente

Como o MCP já existe em outro serviço, a estratégia recomendada é:

```text
MCP externo
        ↓
REST API
        ↓
QueryService
        ↓
Gold
```

Portanto, não é necessário criar:

```text
src/queo_data_platform/mcp/
```

neste projeto.

A QUEO Data Platform permanece uma:

```text
Data Platform + Data API
```

e o outro serviço permanece responsável por:

```text
MCP
```

---

# 23. Benefício para manutenção

Imagine que no futuro a Query Layer deixe de utilizar:

```text
DuckDB
```

e passe a utilizar:

```text
outro mecanismo de consulta
```

Se o MCP acessa a API:

```text
MCP
 ↓
HTTP contract
```

nada precisa mudar no MCP.

A mudança fica:

```text
REST API
 ↓
Query Layer nova
```

Desde que:

```text
/api/v1/...
```

continue respeitando o mesmo contrato.

Esse é um dos maiores benefícios da separação.

---

# 24. Benefício para escalabilidade física

Hoje a arquitetura pode funcionar localmente:

```text
MCP
 ↓
localhost:8000
 ↓
QUEO Data Platform
```

No futuro pode se tornar:

```text
MCP container
      ↓
network
      ↓
Data Platform API container
      ↓
Lakehouse
```

Ou:

```text
MCP
 ↓
HTTPS
 ↓
API Gateway
 ↓
Data Platform API
 ↓
Lakehouse
```

Sem modificar a estrutura lógica da integração.

---

# 25. Possível evolução futura com autenticação

Hoje a API é essencialmente read-only.

No futuro, a fronteira HTTP permite adicionar:

```text
API key
JWT
OAuth
mTLS
service account
```

sem conceder ao MCP acesso direto ao armazenamento.

Arquitetura:

```text
MCP
 ↓
credential
 ↓
REST API
 ↓
authorization
 ↓
Query Layer
```

Isso é mais seguro do que compartilhar:

```text
acesso direto à Gold
```

entre serviços.

---

# 26. Possível evolução para múltiplos consumidores

A API também evita que cada consumidor implemente sua própria lógica.

Sem uma Data API:

```text
Dashboard → Gold
MCP       → Gold
Backoffice→ Gold
Mobile    → Gold
```

Cada consumidor precisaria aprender:

```text
Delta
schemas
filtros
partições
```

Com a arquitetura atual:

```text
                   ┌── Dashboard
                   │
Gold → Query → API ├── MCP
                   │
                   ├── Backoffice
                   │
                   └── Mobile
```

Todos compartilham o mesmo contrato.

---

# 27. Regra arquitetural consolidada

A regra geral passa a ser:

```text
regra de negócio analítica
        ↓
Gold
```

```text
regra de consulta
        ↓
Query Layer
```

```text
contrato HTTP
        ↓
REST API
```

```text
semântica para LLM
        ↓
MCP Service
```

Isso evita que uma única camada acumule responsabilidades.

---

# 28. Arquitetura final recomendada

```text
┌────────────────────────────────────────────────────────┐
│                 QUEO DATA PLATFORM                     │
│                                                        │
│ Raw                                                    │
│  ↓                                                     │
│ Bronze                                                 │
│  ↓                                                     │
│ Silver                                                 │
│  ↓                                                     │
│ Gold                                                   │
│  ↓                                                     │
│ QueryService                                           │
│  ↓                                                     │
│ REST API                                               │
│                                                        │
└───────────────────────────┬────────────────────────────┘
                            │
                            │ HTTP / JSON
                            │
             ┌──────────────┼───────────────┐
             │              │               │
             ▼              ▼               ▼
         Dashboard      MCP Service     Backoffice
                            │
                            ▼
                         MCP Tools
                            │
                            ▼
                      LLM / MCP Client
```

O princípio central é:

```text
Gold
possui os produtos
```

```text
Query Layer
sabe consultar
```

```text
REST API
sabe expor
```

```text
MCP
sabe apresentar essas capacidades
para agentes e modelos
```

---

# 29. Estratégia para novas necessidades do MCP

Caso o MCP precise de uma capacidade que a API atual não oferece, o primeiro questionamento deve ser:

```text
a Query Layer já consegue responder?
```

## Se sim

Adicionar apenas:

```text
novo endpoint REST
        ↓
nova tool MCP
```

## Se não

Implementar:

```text
QueryService
        ↓
teste da Query Layer
        ↓
REST endpoint
        ↓
teste HTTP
        ↓
MCP tool
```

## Se a própria Gold não consegue responder

O fluxo passa a ser:

```text
novo requisito analítico
        ↓
Gold
        ↓
Query Layer
        ↓
REST API
        ↓
MCP
```

Isso mantém o crescimento da plataforma previsível.

---

# 30. Conclusão

A existência de um MCP externo não exige uma implementação MCP dentro da QUEO Data Platform.

Pelo contrário, a arquitetura atual já criou a fronteira adequada para essa integração:

```text
Gold
 ↓
Query Layer
 ↓
REST API
 ↓
MCP externo
```

O consumo HTTP deve ser a opção padrão quando:

```text
MCP e Data Platform
são serviços diferentes
```

O acesso direto ao `QueryService` continua disponível como mecanismo de extensão quando:

```text
o consumidor pertence
ao mesmo runtime/aplicação
```

Assim a arquitetura suporta simultaneamente:

```text
baixo acoplamento externo
```

e:

```text
extensibilidade interna
```

sem duplicar regras de consulta ou acesso à Gold.