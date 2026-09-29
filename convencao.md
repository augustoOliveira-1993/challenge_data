Este documento define as convenções básicas de nomenclatura e padronização de código para o projeto **Python Data Engineering Challenge – JIRA**.

O objetivo é garantir organização, legibilidade e consistência no pipeline.

---

## 🐍 Padrão de Codificação – Python

- Seguir o padrão **PEP 8**
- Indentação com **4 espaços**
- Código e comentários em **inglês**
- Arquivos, funções e variáveis em **snake_case**

---

## 📁 Nomes de Arquivos e Pastas

### Pastas
- Letras minúsculas
- `snake_case`

### Exemplos:
`src/`
`data/`
`resources/`


### Arquivos Python

Formato:
`.py`


Exemplos:
`ingest_bronze.py`
`transform_silver.py`
`build_gold.py`
`sla_calculation.py`

---
*Estrutura de exemplo: *

project-root/
│
├── data/
│ ├── bronze/
│ ├── silver/
│ └── gold/
│
├── src/
│ ├── bronze/
│ │ └── ingest_bronze.py
│ ├── silver/
│ │ └── transform_silver.py
│ ├── gold/
│ │ └── build_gold.py
│ └── sla_calculation.py
│
├── requirements.txt
├── README.md
└── .gitignore

## 🧩 Nomes de Funções

- Devem iniciar com um **verbo**
- Nome descritivo e objetivo

Exemplos:
```python
def read_json_file():
    pass

def calculate_resolution_hours():
    pass

def check_sla_compliance():
    pass
```

📦 Nomes de Variáveis
- Utilizar snake_case
- Evitar nomes genéricos

Exemplos:

``issue_id``
``created_at``
``resolved_at``
``resolution_hours``
``sla_expected_hours``

🗄️ Nomes de Tabelas / Arquivos de Dados
Formato:
``<camada>_<entidade>.<formato>``

### Exemplos:

``bronze_issues.json``
``silver_issues.parquet``
``gold_sla_issues.csv``

### Relatórios:

``gold_sla_by_analyst.csv``
``gold_sla_by_issue_type.csv``

###  🧾 Nomes de Colunas
- Sempre em snake_case

- Datas devem terminar com _at ou começar com dt

- Campos booleanos devem iniciar com is_

Exemplos:

``issue_id``
``issue_type``
``priority``
``assignee_name``
``created_at``
``resolved_at``
``resolution_hours``
``sla_expected_hours``
``is_sla_met``

### ⏱️ Datas e Horários
- Utilizar padrão ISO 8601
- Trabalhar preferencialmente em UTC

Exemplo:

``2025-01-10T08:30:00Z``