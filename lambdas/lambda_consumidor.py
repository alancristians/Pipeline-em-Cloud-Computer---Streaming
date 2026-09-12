import json
import boto3
import pymysql
import os

s3_client = boto3.client('s3')
DEST_BUCKET = os.environ['DEST_BUCKET']

def conectar_banco():
    return pymysql.connect(
        host=os.environ['DB_HOST'],
        user=os.environ['DB_USER'],
        password=os.environ['DB_PASS'],
        database=os.environ['DB_NAME'],
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=5
    )

def lambda_handler(event, context):
    conexao = conectar_banco()
    mensagens_processadas = []
    
    try:
        with conexao.cursor() as cursor:
            for record in event['Records']:
                body = json.loads(record['body'])
                cnpj = body.get('CNPJ IF') or body.get('CNPJ')
                
                sql = "SELECT Nome, Segmento FROM dim_instituicao WHERE CNPJ = %s"
                cursor.execute(sql, (cnpj,))
                resultado = cursor.fetchone()
                
                if resultado:
                    body['nome_instituicao_enriquecido'] = resultado['Nome']
                    body['segmento_enriquecido'] = resultado['Segmento']
                else:
                    body['nome_instituicao_enriquecido'] = 'NAO ENCONTRADO'
                    body['segmento_enriquecido'] = 'NAO ENCONTRADO'
                    
                mensagens_processadas.append(body)
                
        arquivo_chave = f"delivery/dados_enriquecidos_{context.aws_request_id}.json"
        s3_client.put_object(
            Bucket=DEST_BUCKET,
            Key=arquivo_chave,
            Body=json.dumps(mensagens_processadas, ensure_ascii=False, indent=2)
        )
    finally:
        conexao.close()
        
    return {'status': 200, 'body': f'{len(mensagens_processadas)} registros enriquecidos'}