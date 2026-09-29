# Python Data Engineering Challenge – JIRA

Pipeline de dados em Python que lê chamados fictícios do JIRA (JSON aninhado), organiza os dados na **Arquitetura Medallion** (Bronze → Silver → Gold) e calcula o **SLA de resolução em horas úteis**, excluindo fins de semana e feriados nacionais obtidos de uma API pública.

---

## Sumário

- [Arquitetura](#arquitetura)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Como executar](#como-executar)
- [Fonte de dados e status da integração com Azure](#fonte-de-dados-e-status-da-integração-com-azure)
- [Camadas do pipeline](#camadas-do-pipeline)
- [Lógica de cálculo do SLA](#lógica-de-cálculo-do-sla)
- [Dicionário de dados](#dicionário-de-dados)
- [Resultados da execução](#resultados-da-execução)
- [Segurança das credenciais](#segurança-das-credenciais)
- [Decisões e premissas](#decisões-e-premissas)

---

## Arquitetura

```
Azure Blob Storage (Service Principal, somente leitura)
        │        └── fallback: resources/jira_issues_raw.json
        ▼
BRONZE  data/bronze/bronze_issues.json          cópia fiel (byte a byte) da origem
        ▼
SILVER  data/silver/silver_issues.parquet       1 linha por chamado, colunas padronizadas e tipadas
        data/silver/silver_issues_rejected.csv  registros descartados + motivo
        ▼                ◄── BrasilAPI (feriados nacionais)
GOLD    data/gold/gold_sla_issues.csv           SLA por chamado (somente Done/Resolved)
        data/gold/gold_sla_by_analyst.csv       relatório: SLA médio por analista
        data/gold/gold_sla_by_issue_type.csv    relatório: SLA médio por tipo de chamado
```

Cada camada lê **o arquivo persistido pela camada anterior**, e toda a persistência é local. Nada é gravado no Blob Storage.

---

## Estrutura do projeto

```
├── main.py                        # orquestra o pipeline: Bronze -> Silver -> Gold
├── src/
│   ├── config.py                  # caminhos do projeto e leitura das variáveis de ambiente
│   ├── bronze/ingest_bronze.py    # ingestão (Azure Blob com fallback local)
│   ├── silver/transform_silver.py # explode, padronização, datas e qualidade de dados
│   ├── gold/build_gold.py         # tabela final de SLA e relatórios agregados
│   ├── sla_calculation.py         # regras de SLA (funções puras, sem I/O)
│   └── holidays_api.py            # consumo da BrasilAPI (feriados nacionais)
├── tests/                         # testes unitários e de ponta a ponta (pytest)
├── data/{bronze,silver,gold}/     # dados persistidos de cada camada
├── resources/jira_issues_raw.json # cópia local da fonte (fallback)
├── .env.example                   # modelo das variáveis de ambiente (sem valores reais)
├── requirements.txt
└── pytest.ini
```

---

## Como executar

Pré-requisitos: **Python 3.12** e acesso à internet (API de feriados).

```bash
# 1. Ambiente virtual
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS

# 2. Dependências
pip install -r requirements.txt

# 3. (Opcional) Credenciais do Azure
cp .env.example .env            # preencher com os valores recebidos; .env não é versionado

# 4. Pipeline completo
python main.py

# 5. Testes
python -m pytest
```

Sem o `.env`, ou se o Azure estiver indisponível, o pipeline usa automaticamente `resources/jira_issues_raw.json` e registra um WARNING informando a troca de fonte.

---

## Fonte de dados e status da integração com Azure

A ingestão pelo **Azure Blob Storage com autenticação via Service Principal** está implementada em `src/bronze/ingest_bronze.py`:

- `ClientSecretCredential` + `BlobServiceClient`;
- somente `download_blob()`, ou seja, apenas leitura;
- política de retry reduzida (1 retry), para que uma falha leve ao fallback em poucos segundos.

> **Status da validação:** a leitura real do Blob **não pôde ser validada**. Durante a execução, o endpoint do storage account informado no material original do desafio **não estava mais acessível**: o nome não é resolvido no DNS (`Non-existent domain`), tanto no DNS local quanto no público. Conforme permitido pelo desafio, **a execução foi validada usando a fonte local de fallback** (`resources/jira_issues_raw.json`).
>
> Os testes automatizados cobrem a lógica de escolha da fonte com o Azure simulado: Azure disponível, Azure não configurado e falha do Azure. Eles não substituem um teste real contra o storage.

Quando o Azure falha, o log mostra:

```
WARNING | Official Azure source FAILED (ServiceRequestError: ...). Pipeline will continue using local file: ...
```

---

## Camadas do pipeline

### Bronze: ingestão (`ingest_bronze.py`)

- Lê o JSON da fonte (Azure ou arquivo local).
- Faz o parse do JSON **apenas para confirmar que é válido** e grava **os bytes originais** em `bronze_issues.json`. Não há nenhuma transformação: o SHA-256 da Bronze é igual ao da fonte, e isso é verificado em teste.
- **Formato JSON**: é o mesmo formato da origem, o que preserva fidelidade total.

### Silver: limpeza e organização (`transform_silver.py`)

1. **Explode** das listas `assignee` e `timestamps` e extração dos campos internos (`assignee.id`, `assignee.name`, `assignee.email`, `timestamps.created_at`, `timestamps.resolved_at`).
2. **Padronização** dos nomes de colunas em snake_case (`id` → `issue_id`, `assignee` → `assignee_*`). `project_id` e `extracted_at` são mantidos para rastrear a origem de cada linha.
3. **Conversão de datas** ISO 8601 para `datetime` em UTC, com formato estrito (`%Y-%m-%dT%H:%M:%SZ`). Valores inválidos viram `NaT`.
4. **Qualidade de dados**: cada registro é verificado contra as regras abaixo. Os que falham vão para `silver_issues_rejected.csv`, com os valores originais e o motivo (a primeira regra violada):

   | Regra (`rejection_reason`) | Descrição |
   |---|---|
   | `invalid_created_at` | data de abertura ausente ou inválida |
   | `invalid_resolved_at` | data de resolução preenchida, mas inválida |
   | `resolved_before_created` | resolução anterior à abertura |
   | `invalid_status` | status fora de Open/Done/Resolved |
   | `invalid_priority` | prioridade fora de High/Medium/Low |
   | `missing_resolved_at` | chamado Done/Resolved sem data de resolução |
   | `duplicated_issue_id` | `issue_id` repetido (mantém a primeira ocorrência) |

5. **Chamados Open são mantidos** (com `resolved_at` nulo).
6. **Formato Parquet**: preserva os tipos entre as camadas (datas em UTC, texto), então a Gold não precisa refazer a conversão. Os rejeitados são gravados em CSV, para facilitar a inspeção manual.

### Gold: regras de negócio (`build_gold.py`)

1. Lê a Silver e mantém **somente Done e Resolved**. Chamados Open não têm data de resolução e ficam fora do SLA.
2. Busca os feriados nacionais dos anos cobertos pelos dados (da primeira abertura à última resolução).
3. Aplica as funções de `sla_calculation.py` para gerar `resolution_hours`, `sla_expected_hours` e `is_sla_met`.
4. Gera os relatórios agregados por analista e por tipo de chamado.
5. **Formato CSV**: legível, aceito no enunciado para os relatórios e aberto diretamente em Excel ou em qualquer ferramenta. As datas são gravadas em ISO 8601 UTC (`2025-01-10T08:30:00Z`).

### Tratamento por status

| Status | Bronze | Silver | Gold / SLA |
|---|---|---|---|
| Open | ✅ | ✅ (`resolved_at` nulo) | ❌ (sem data de resolução) |
| Done | ✅ | ✅ | ✅ |
| Resolved | ✅ | ✅ | ✅ (tratado igual a Done, pois ambos são chamados encerrados) |
| Qualquer status com data inválida | ✅ | ❌ (vai para rejeitados) | ❌ |

---

## Lógica de cálculo do SLA

Implementada em `src/sla_calculation.py`, com funções puras. Os feriados chegam como parâmetro, então a lógica pode ser testada sem rede.

| Função | Responsabilidade |
|---|---|
| `get_sla_expected_hours(priority)` | SLA esperado por prioridade (`if/elif/else`): **High = 24h, Medium = 72h, Low = 120h**. Prioridade desconhecida gera `ValueError` |
| `is_business_day(day, holidays)` | Dia útil = segunda a sexta **e** fora da lista de feriados |
| `calculate_resolution_hours(created_at, resolved_at, holidays)` | Tempo de resolução em horas úteis |
| `check_sla_compliance(resolution_hours, sla_expected_hours)` | `True` se `resolution_hours <= sla_expected_hours` |

### Cálculo das horas úteis

- **24 horas por dia útil**: sábados, domingos e feriados são descartados por inteiro.
- O cálculo percorre (`for`) cada dia do calendário entre a abertura e a resolução. Em cada dia útil, soma o trecho do intervalo que cai dentro daquele dia:

```
para cada dia entre created_at.date() e resolved_at.date():
    se o dia não for útil: pula
    início = max(created_at, 00:00 do dia)
    fim    = min(resolved_at, 00:00 do dia seguinte)
    total += fim - início
horas úteis = total em horas, arredondado para 2 casas
```

- Consequências dessa regra:
  - um chamado aberto no sábado começa a contar na segunda às 00:00;
  - um chamado resolvido no domingo para de contar na sexta às 24:00;
  - um chamado aberto e resolvido dentro do mesmo fim de semana ou feriado tem 0h.
- Os limites dos dias são calculados em **UTC**, o fuso dos dados e o recomendado na convenção.

**Exemplos reais da tabela Gold (conferidos manualmente):**

| Chamado | Abertura (UTC) | Resolução (UTC) | Horas corridas | Horas úteis | Explicação |
|---|---|---|---|---|---|
| JIRA-0002 (High) | dom 2025-03-09 12:39:26 | seg 2025-03-10 10:39:26 | 22 | **10.66** | domingo não conta; seg 00:00 → 10:39:26 |
| JIRA-0068 (Medium) | qui 2025-05-01 01:04:58 | sex 2025-05-02 19:04:58 | 42 | **19.08** | 01/05 (Dia do Trabalho) não conta; sex 00:00 → 19:04:58 |
| JIRA-0120 (Medium) | qua 2025-12-24 02:09:45 | qui 2025-12-25 09:09:45 | 31 | **21.84** | 24/12 02:09:45 → 24:00; o Natal não conta |
| JIRA-0013 (Medium) | ter 2025-02-25 11:02:21 | sáb 2025-03-01 04:02:21 | 89 | **84.96** | ter 12.96h + qua/qui/sex 72h; sábado não conta. **Violado** (> 72h) |

### API de feriados

- **BrasilAPI**: `GET https://brasilapi.com.br/api/feriados/v1/{ano}`. É pública, não exige autenticação e retorna só feriados nacionais.
- `src/holidays_api.py` faz uma requisição por ano (timeout de 10s) e devolve um `set` de datas. Com os dados atuais: 2025 e 2026, 14 feriados cada.
- Se a API falhar, o pipeline **interrompe com erro explícito** (código de saída 1). Calcular SLA sem feriados geraria resultados incorretos sem aviso.

---

## Dicionário de dados

### `data/gold/gold_sla_issues.csv`: SLA por chamado (somente Done/Resolved)

| Coluna | Tipo | Descrição |
|---|---|---|
| `issue_id` | texto | ID do chamado (ex.: `JIRA-0002`) |
| `issue_type` | texto | Tipo do chamado: `Bug`, `Task`, `Story` |
| `assignee_name` | texto | Analista responsável |
| `priority` | texto | Prioridade: `High`, `Medium`, `Low` |
| `created_at` | data/hora ISO 8601 UTC | Data/hora de abertura |
| `resolved_at` | data/hora ISO 8601 UTC | Data/hora de resolução |
| `resolution_hours` | decimal (2 casas) | Tempo de resolução em horas úteis |
| `sla_expected_hours` | inteiro | SLA esperado em horas (24 / 72 / 120) |
| `is_sla_met` | booleano | `True` = SLA atendido; `False` = SLA violado |

### `data/gold/gold_sla_by_analyst.csv`: SLA médio por analista

| Coluna | Tipo | Descrição |
|---|---|---|
| `assignee_name` | texto | Analista |
| `issue_count` | inteiro | Quantidade de chamados Done/Resolved |
| `avg_resolution_hours` | decimal (2 casas) | SLA médio: média de `resolution_hours`, em horas úteis |

### `data/gold/gold_sla_by_issue_type.csv`: SLA médio por tipo de chamado

| Coluna | Tipo | Descrição |
|---|---|---|
| `issue_type` | texto | Tipo do chamado |
| `issue_count` | inteiro | Quantidade de chamados Done/Resolved |
| `avg_resolution_hours` | decimal (2 casas) | SLA médio: média de `resolution_hours`, em horas úteis |

### `data/silver/silver_issues.parquet`: chamados válidos (inclui Open)

| Coluna | Tipo | Origem no JSON |
|---|---|---|
| `issue_id` | texto | `issues[].id` |
| `issue_type` | texto | `issues[].issue_type` |
| `status` | texto | `issues[].status` |
| `priority` | texto | `issues[].priority` |
| `assignee_id` / `assignee_name` / `assignee_email` | texto | `issues[].assignee[].id / name / email` |
| `created_at` | datetime UTC | `issues[].timestamps[].created_at` |
| `resolved_at` | datetime UTC (nulo se Open) | `issues[].timestamps[].resolved_at` |
| `project_id` | texto | `project.project_id` |
| `extracted_at` | datetime UTC | `project.extracted_at` |

O arquivo `data/silver/silver_issues_rejected.csv` tem as mesmas colunas, com os **valores originais** (sem conversão), mais a coluna `rejection_reason`.

---

## Resultados da execução

| Camada | Registros |
|---|---|
| Bronze | 1000 chamados (412.850 bytes, SHA-256 idêntico à fonte) |
| Silver | 990 válidos (186 Open, 413 Done, 391 Resolved) + 10 rejeitados |
| Gold | 804 chamados (748 SLA atendido, 56 violado) |

Os 10 rejeitados (JIRA-0991 a JIRA-1000) têm `created_at = "2026-02-30T25:61:00Z"` (data e hora impossíveis) e `resolved_at = "not_a_date"`.

**SLA médio por analista**

| assignee_name | issue_count | avg_resolution_hours |
|---|---|---|
| Adyna | 148 | 37.43 |
| Francinne | 175 | 37.94 |
| Gionni Lucio | 175 | 39.18 |
| Guilherme Francisco | 157 | 37.28 |
| Matheus Malta | 149 | 34.86 |

**SLA médio por tipo de chamado**

| issue_type | issue_count | avg_resolution_hours |
|---|---|---|
| Bug | 237 | 37.63 |
| Story | 290 | 35.67 |
| Task | 277 | 39.06 |

---

## Segurança das credenciais

- As credenciais ficam **somente em variáveis de ambiente**, carregadas de um `.env` local com `python-dotenv`. Nenhum valor aparece no código.
- `.env` e `recursos.md` (que contém as credenciais originais do desafio) estão no `.gitignore` e **nunca foram versionados**. O repositório tem apenas o `.env.example`, com os nomes das variáveis.
- Os logs mostram só os **nomes** das variáveis ausentes, nunca os valores.
- O acesso ao Blob é de somente leitura (`download_blob`). O Service Principal do desafio só tem acesso ao arquivo de origem.

Variáveis esperadas: `ACCOUNT_URL`, `CONTAINER_NAME`, `BLOB_NAME`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`.

---

## Decisões e premissas

| Tema | Decisão |
|---|---|
| Horas úteis | 24h por dia útil. O enunciado não define horário de expediente, e um SLA High de 24h só faz sentido num relógio de 24h |
| Fuso horário | UTC para definir dias e fins de semana, conforme a convenção. Um chamado de sexta às 22h no horário de Brasília (01h UTC de sábado) cai no sábado |
| Feriados | Nacionais, conforme a BrasilAPI. Ela classifica o **Carnaval** como nacional, embora legalmente seja ponto facultativo; seguimos a API. Feriados estaduais e municipais não são considerados |
| Empate | `resolution_hours == sla_expected_hours` conta como SLA **atendido** (`<=`) |
| Arredondamento | Horas úteis arredondadas para 2 casas antes da comparação com o SLA. Isso não altera nenhum resultado neste dataset (verificado) |
| "SLA médio" nos relatórios | Média do tempo de resolução em horas úteis (`avg_resolution_hours`) |
| Chamados com 0h | 81 chamados foram abertos e resolvidos inteiramente em fins de semana ou feriados e ficam com 0 horas úteis. É consequência direta da regra |
| Listas `assignee` / `timestamps` | Sempre têm 1 elemento neste dataset. Se houvesse mais de um, o explode duplicaria o chamado; a regra `duplicated_issue_id` protege a Silver contra isso |
| `extracted_at` | O JSON informa extração em 2026-01-22, mas há chamados criados ou resolvidos depois dessa data. Não filtramos, porque são dados fictícios; a coluna é mantida para rastrear a origem |
| Datas inválidas | Qualquer chamado com data inválida é descartado na Silver, inclusive os Open, conforme permitido pelo enunciado |
| Reprocessamento | Cada execução sobrescreve as saídas. Rodar de novo não duplica dados |
| Dados versionados | `data/` é versionado para que o resultado possa ser consultado sem executar o pipeline |
