# 🚀 Pipeline Streaming: Ingestão e Enriquecimento de Reclamações Bancárias (BACEN)

Projeto prático de **Pipeline de Dados em Nuvem (Event-Driven Architecture)** desenvolvido para processamento e enriquecimento em tempo real de arquivos de reclamações bancárias do Banco Central (BACEN). 

A arquitetura é baseada em serviços **Serverless na AWS (S3, SQS e Lambda)** com enriquecimento relacional dinâmico feito em memória RAM via **SQLite**.

---

## 🏗️ Arquitetura da Solução

```text
[ Bucket S3 RAW ] 
       │ (s3:ObjectCreated)
       ▼
[ Lambda 1: Produtor Batch ] ➔ (Leitura em latin1 / Envio em Lotes)
       │
       ▼
[ AWS SQS: Fila Buffer ] ➔ (Desacoplamento e Mensageria)
       │
       ▼
[ Lambda 2: Consumidor SQL ] ◄──► [ SQLite RAM (dim_instituicao) ]
       │ (Enriquecimento Relacional)
       ▼
[ Bucket S3 Delivery ] ➔ (JSONs Enriquecidos por Request ID)


⚙️ Componentes do Pipeline
Amazon S3 (raw-dados-atividade7-alan): Ingestão dos arquivos CSV brutos do BACEN.

AWS Lambda Produtora (fn-produtor-s3-sqs): Leitura otimizada em latin1 e envio agrupado para a fila SQS.

Amazon SQS (fila-reclamacoes-ingestao): Fila de mensageria padrão usada para desacoplamento e controle de vazão (backpressure).

AWS Lambda Consumidora (fn-consumidor-sqs-mysql-s3): Carga e consulta SQL em memória (sqlite3) para enriquecimento relacional e geração do JSON final.

Amazon S3 (delivery-dados-atividade7-alan): Persistência dos payloads tratados na pasta delivery/.


📂 Estrutura do Repositório
.
├── lambdas/
│   ├── lambda_produtor.py     # Código da Lambda Produtora (S3 -> SQS)
│   └── lambda_consumidor.py   # Código da Lambda Consumidora (SQS -> SQLite -> S3)
├── data/
│   └── 2021_tri_01.csv        # Dataset de exemplo de reclamações bancárias
├── gerar_slides.py            # Gerador automatizado da apresentação PPTX
└── README.md                  # Documentação principal


🛠️ Tecnologias Utilizadas
Linguagem: Python 3.12
SDK AWS: boto3
Banco de Dados: sqlite3 (Instância efémera em memória RAM :memory:)
Serviços Cloud: Amazon S3, AWS Lambda, Amazon SQS, AWS CloudWatch

🔧 Variáveis de Ambiente Configuradas

Lambda | Nome da Variável | Valor

fn-produtor-s3-sqs |	SQS_QUEUE_URL |	https://sqs.us-east-1.amazonaws.com/456768312676/fila-reclamacoes-ingestao

fn-consumidor-sqs-mysql-s3 |	DEST_BUCKET |	delivery-dados-atividade7-alan

💥 Desafios Técnicos Solucionados
Tratamento de Encoding (UnicodeDecodeError): Leitura do CSV forçada para latin1 (iso-8859-1) para preservar acentuações em português.

Otimização de Performance e Latência: Aumento do timeout para 2 min e envio agrupado em lotes de 10 mensagens (sqs_client.send_message_batch).

Fallback Relacional para Conglomerados: Implementação de chave de busca dinâmica (CNPJ ➔ Nome da Instituição) para resolver casos de conglomerados sem CNPJ no arquivo original.

📊 Estrutura do Payload Final (JSON Enriquecido)
[
  {
    "Ano": "2021",
    "Trimestre": "1º",
    "Categoria": "Grupo Secundário",
    "Tipo": "Banco/financeira",
    "CNPJ IF": "07747410",
    "Instituição financeira": "SAX S.A. - CRÉDITO, FINANCIAMENTO E INVESTIMENTO",
    "Quantidade total de reclamações": "8",
    "nome_instituicao_enriquecido": "SAX S.A. - CRÉDITO, FINANCIAMENTO E INVESTIMENTO",
    "segmento_enriquecido": "Grupo Secundário"
  }
]

👨‍💻 Autor
Alan Cristian Oliveira Freire da Silva
Pós-Graduação em Engenharia de Dados e Big Data — PECE Poli-USP