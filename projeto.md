# Python Data Engineering Challenge – JIRA 

## Objetivo

O objetivo deste desafio é avaliar a capacidade do participante em desenvolver um pipeline de Engenharia de Dados em Python, aplicando conceitos fundamentais como ingestão de dados, organização em camadas, transformações e aplicação de regras de negócio.

O foco principal da avaliação será a correta aplicação da Arquitetura Medallion, a clareza do código, segurança, qualidade dos dados e a implementação da lógica de cálculo de SLA.

---

## Data Source

Será disponibilizado um arquivo JSON contendo dados fictícios extraídos do JIRA.

Características do data source:
- Arquivo em formato JSON
- Estrutura aninhada (listas e objetos internos)
- Dados desnormalizados
- Contém chamados com status **Open**, **Done** e **Resolved**
- O JSON possui alguns dados invalidos para testar a limpeza dos dados, os chamados com datas invalidas podem ser ignorados.

O arquivo estará armazenado em um **Azure Blob Storage**, que será utilizado **exclusivamente como origem dos dados**.

Os participantes **não deverão gravar dados no Blob Storage**.  
Toda a persistência dos dados deve ocorrer **localmente no projeto**.

O acesso ao Blob Storage deverá ser realizado utilizando autenticação via **Service Principal**, conforme instruções disponíveis no arquivo `<recursos.md>`.

````Como alternativa, o mesmo arquivo JSON também estará disponível no repositório do projeto, caso o participante não consiga avançar com a etapa de ingestão````


---

## Arquitetura do Pipeline

O pipeline deve ser desenvolvido seguindo a **Arquitetura Medallion**, organizada nas seguintes camadas:

### Bronze
Responsável pela ingestão dos dados brutos.
- Leitura do JSON original
- Nenhuma ou mínima transformação
- Dados mantidos o mais próximos possível da origem

### Silver
Responsável pela limpeza e organização dos dados.
- Tratamento do JSON aninhado (exemplo: explode de listas)
- Extração de campos de estruturas internas
- Padronização de nomes de colunas
- Conversão e tratamento de datas
- Preparação dos dados para o cálculo de métricas

### Gold
Responsável pela aplicação das regras de negócio.
- Cálculo das métricas de SLA
- Criação da tabela final de análise
- Geração de relatórios agregados

A persistência dos dados em cada camada deve ser feita **localmente no projeto**, ficando a critério do participante o formato utilizado (ex: CSV, JSON, Parquet, etc.).  
A escolha do formato deve ser explicada na documentação.

---

## Transformações Esperadas

- Leitura de arquivos JSON com estruturas aninhadas
- Manipulação de listas e dicionários
- Criação de colunas derivadas de objetos internos
- Organização clara do pipeline por camadas (Bronze, Silver e Gold)

---

## Métrica – SLA por Chamado

O participante deverá calcular o tempo de resolução de cada chamado considerando:
- Data/hora de abertura
- Data/hora de resolução

Chamados com status **Open** não possuem data de resolução e não devem ser considerados no cálculo final de SLA, mas devem permanecer no pipeline até a camada Silver.

---

## Regras de SLA

| Prioridade | SLA esperado |
|-----------|--------------|
| High      | 24 horas     |
| Medium    | 72 horas     |
| Low       | 120 horas    |

O cálculo do SLA deve considerar:
- Apenas dias úteis
- Exclusão de finais de semana
- Exclusão de feriados nacionais

Para identificar feriados nacionais, deverá ser consumida uma API pública.  
A escolha da API fica a critério do participante.

---

## Implementação da Lógica de SLA

A lógica de cálculo de SLA deve ser implementada em um arquivo Python separado (exemplo: `sla_calculation.py`).

Devem existir funções responsáveis por:
- Calcular o tempo de resolução em horas úteis
- Definir o SLA esperado de acordo com a prioridade
- Indicar se o SLA foi atendido ou violado

Espera-se o uso de estruturas básicas da linguagem Python, como:
- if / elif / else
- for
- Funções reutilizáveis
- Manipulação de datas

As funções devem ser importadas e utilizadas no pipeline principal, sendo aplicadas na construção da camada Gold.

---

## Saída Esperada – Camada Gold

### Tabela Final – SLA por Chamado

A tabela final deve conter, no mínimo, os seguintes campos:
- ID do chamado
- Tipo do chamado
- Analista responsável
- Prioridade
- Data de abertura
- Data de resolução
- Tempo de resolução em horas úteis
- SLA esperado (em horas)
- Indicador de SLA atendido ou não atendido

Apenas chamados com status **Done** ou **Resolved** devem compor essa tabela.

---

## Relatórios Simples (Obrigatórios)

A partir da camada Gold, devem ser gerados os seguintes relatórios agregados:

### SLA Médio por Analista
- Analista
- Quantidade de chamados
- SLA médio (em horas)

### SLA Médio por Tipo de Chamado
- Tipo do chamado
- Quantidade de chamados
- SLA médio (em horas)

Não é necessário criar dashboards ou visualizações gráficas.  
Os relatórios podem ser entregues em formato `.CSV` ou `.XLSX`.

---

## Entregáveis

Os participantes deverão entregar:
- Projeto completo em Python
- Pipeline organizado por camadas (Bronze, Silver e Gold)
- Persistência dos dados localmente no projeto
- Projeto versionado em um repositório GitHub
- Arquivo `README.md` contendo:
  - Instruções para execução do projeto
  - Explicação da arquitetura do pipeline
  - Descrição da lógica de cálculo do SLA
  - Dicionário de dados da tabela final e dos relatórios
- Arquivo `requirements.txt`

---

## Premissas do Projeto

- Utilizar Python
- Utilizar bibliotecas nativas do Python  
- Pandas está liberado para leitura e transformações
- O projeto deve ser entregue no GitHub
- Os objetos devem seguir a convenção de nomenclatura definida em `<arquivo_convencao.md>`

---

## Não Será Avaliado

- Modelagem dimensional
- Técnicas avançadas de performance
- Utilização de SQL
- Ferramentas de BI ou criação de dashboards

---

## Diferenciais (Não Obrigatórios)

- Código modular e reutilizável
- Uso de variáveis de ambiente
- Utilização de ambiente virtual
- Histórico de commits bem estruturado
- Tratamentos simples de qualidade de dados

---

## Avaliação

Serão avaliados:
- Organização do pipeline e correta aplicação da Arquitetura Medallion
- Clareza, legibilidade e estrutura do código
- Correta implementação da lógica de SLA
- Capacidade de tratar JSON aninhado
- Qualidade da documentação
