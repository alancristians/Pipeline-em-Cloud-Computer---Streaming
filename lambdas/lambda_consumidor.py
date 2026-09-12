import json
import boto3
import os
import sqlite3

s3_client = boto3.client('s3')
DEST_BUCKET = os.environ['DEST_BUCKET']

def criar_banco_memoria():
    # Cria um banco relacional em memória RAM para a execução da Lambda
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE dim_instituicao (
            cnpj TEXT PRIMARY KEY,
            nome TEXT,
            segmento TEXT
        )
    ''')
    
    # Carga da dimensão relacional
    dados_instituicoes = [
        ('00000000', 'BANCO DO BRASIL S.A.', 'Banco Múltiplo'),
        ('60701190', 'ITAU UNIBANCO S.A.', 'Banco Múltiplo'),
        ('60746948', 'BANCO BRADESCO S.A.', 'Banco Múltiplo'),
        ('00360305', 'CAIXA ECONOMICA FEDERAL', 'Caixa Econômica')
    ]
    
    cursor.executemany('INSERT INTO dim_instituicao VALUES (?, ?, ?)', dados_instituicoes)
    conn.commit()
    return conn

def lambda_handler(event, context):
    conn = criar_banco_memoria()
    cursor = conn.cursor()
    mensagens_processadas = []

    try:
        for record in event['Records']:
            body = json.loads(record['body'])
            cnpj = str(body.get('CNPJ IF') or body.get('CNPJ') or '').strip()

            # Execução de solicitação SQL relacional para enriquecimento
            cursor.execute("SELECT nome, segmento FROM dim_instituicao WHERE cnpj = ?", (cnpj,))
            resultado = cursor.fetchone()

            if resultado:
                body['nome_instituicao_enriquecido'] = resultado[0]
                body['segmento_enriquecido'] = resultado[1]
            else:
                body['nome_instituicao_enriquecido'] = 'INSTITUICAO NAO ENCONTRADA'
                body['segmento_enriquecido'] = 'NAO INFORMADO'

            mensagens_processadas.append(body)

        # Gravação do payload tratado e enriquecido no S3
        arquivo_chave = f"delivery/dados_enriquecidos_{context.aws_request_id}.json"
        s3_client.put_object(
            Bucket=DEST_BUCKET,
            Key=arquivo_chave,
            Body=json.dumps(mensagens_processadas, ensure_ascii=False, indent=2)
        )
    finally:
        conn.close()

    return {'status': 200, 'body': f'{len(mensagens_processadas)} registros enriquecidos via SQL'}