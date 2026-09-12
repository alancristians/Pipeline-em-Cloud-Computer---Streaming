import json
import boto3
import os
import sqlite3

s3_client = boto3.client('s3')
DEST_BUCKET = os.environ['DEST_BUCKET']

def criar_banco_memoria():
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE dim_instituicao (
            cnpj TEXT PRIMARY KEY,
            nome TEXT,
            segmento TEXT
        )
    ''')
    
    # Carga de dimensões relacionais com os CNPJs reais do CSV
    dados_instituicoes = [
        ('27098060', 'BANCO DIGIO S.A.', 'Banco/financeira'),
        ('08357240', 'BANCO CSF S.A.', 'Banco/financeira'),
        ('92874270', 'BANCO DIGIMAIS S.A.', 'Banco/financeira'),
        ('36321990', 'AGORACRED S/A', 'Banco/financeira'),
        ('27214112', 'AL5 S.A. CRÉDITO', 'Banco/financeira'),
        ('04902979', 'BANCO DA AMAZONIA S.A.', 'Banco/financeira'),
        ('13009717', 'BANCO DO ESTADO DE SERGIPE S.A.', 'Banco/financeira'),
        ('07237373', 'BANCO DO NORDESTE DO BRASIL S.A.', 'Banco/financeira'),
        ('43180355', 'PEFISA S.A.', 'Banco/financeira'),
        ('05503849', 'SANTANA S.A.', 'Banco/financeira')
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

            # Consulta SQL relacional executada contra a tabela em memória
            cursor.execute("SELECT nome, segmento FROM dim_instituicao WHERE cnpj = ?", (cnpj,))
            resultado = cursor.fetchone()

            if resultado:
                body['nome_instituicao_enriquecido'] = resultado[0]
                body['segmento_enriquecido'] = resultado[1]
            else:
                body['nome_instituicao_enriquecido'] = 'INSTITUICAO NAO ENCONTRADA'
                body['segmento_enriquecido'] = 'NAO INFORMADO'

            mensagens_processadas.append(body)

        arquivo_chave = f"delivery/dados_enriquecidos_{context.aws_request_id}.json"
        s3_client.put_object(
            Bucket=DEST_BUCKET,
            Key=arquivo_chave,
            Body=json.dumps(mensagens_processadas, ensure_ascii=False, indent=2)
        )
    finally:
        conn.close()

    return {'status': 200, 'body': f'{len(mensagens_processadas)} registros enriquecidos via SQL'}