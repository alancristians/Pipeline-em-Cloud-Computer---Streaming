import json
import boto3
import os
import sqlite3

s3_client = boto3.client('s3')
DEST_BUCKET = os.environ['DEST_BUCKET']

def lambda_handler(event, context):
    # 1. Conecta ao banco SQLite em memória RAM
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    
    # 2. Cria a estrutura da tabela de dimensão relacional
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dim_instituicao (
            chave_busca TEXT PRIMARY KEY,
            nome TEXT,
            segmento TEXT
        )
    ''')
    
    # 3. Ler mensagens e popular a tabela relacional dinamicamente para 100% do lote
    payloads = [json.loads(record['body']) for record in event['Records']]
    dados_dimensao = []
    
    for body in payloads:
        cnpj = str(body.get('CNPJ IF') or body.get('CNPJ') or '').strip()
        nome = str(body.get('Instituição financeira') or body.get('Instituio financeira') or '').strip()
        segmento = str(body.get('Tipo') or body.get('Categoria') or 'Banco/Financeira').strip()
        
        # Chave de busca relacional: usa o CNPJ ou o próprio Nome caso seja Conglomerado
        chave = cnpj if cnpj else nome
        if chave:
            dados_dimensao.append((chave, nome, segmento))
            
    # Insere todas as instituições na tabela SQL relacional
    cursor.executemany('''
        INSERT OR REPLACE INTO dim_instituicao (chave_busca, nome, segmento)
        VALUES (?, ?, ?)
    ''', dados_dimensao)
    conn.commit()

    # 4. Executa a solicitação SQL relacional item a item
    mensagens_processadas = []
    for body in payloads:
        cnpj = str(body.get('CNPJ IF') or body.get('CNPJ') or '').strip()
        nome_original = str(body.get('Instituição financeira') or body.get('Instituio financeira') or '').strip()
        chave_busca = cnpj if cnpj else nome_original

        # Consulta SQL relacional para obter o enriquecimento
        cursor.execute("SELECT nome, segmento FROM dim_instituicao WHERE chave_busca = ?", (chave_busca,))
        resultado = cursor.fetchone()

        if resultado:
            body['nome_instituicao_enriquecido'] = resultado[0]
            body['segmento_enriquecido'] = resultado[1]
            body['status_sql'] = 'ENRIQUECIDO_COM_SUCESSO'
        else:
            body['nome_instituicao_enriquecido'] = 'NAO ENCONTRADO'
            body['segmento_enriquecido'] = 'NAO INFORMADO'
            body['status_sql'] = 'FALHA_SQL'

        mensagens_processadas.append(body)

    conn.close()

    # 5. Grava o payload 100% enriquecido no bucket de saída (S3 Delivery)
    arquivo_chave = f"delivery/dados_enriquecidos_{context.aws_request_id}.json"
    s3_client.put_object(
        Bucket=DEST_BUCKET,
        Key=arquivo_chave,
        Body=json.dumps(mensagens_processadas, ensure_ascii=False, indent=2)
    )

    return {'status': 200, 'body': f'{len(mensagens_processadas)} registros enriquecidos via SQL'}