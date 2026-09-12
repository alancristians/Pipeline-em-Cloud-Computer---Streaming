import json
import boto3
import os
import sqlite3

s3_client = boto3.client('s3')
DEST_BUCKET = os.environ['DEST_BUCKET']

def buscar_valor(dicionario, termos_chave, valor_padrao=""):
    """Busca valores no dicionário ignorando variações de acentuação e encoding nas chaves."""
    for chave, valor in dicionario.items():
        for termo in termos_chave:
            if termo.lower() in chave.lower() and valor:
                return str(valor).strip()
    return valor_padrao

def lambda_handler(event, context):
    conn = sqlite3.connect(':memory:')
    cursor = conn.cursor()
    
    # Cria a tabela de dimensão relacional
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS dim_instituicao (
            chave_id TEXT PRIMARY KEY,
            nome TEXT,
            segmento TEXT
        )
    ''')
    
    payloads = [json.loads(record['body']) for record in event['Records']]
    
    # 1. Popula a dimensão SQL dinamicamente com 100% dos registros do lote
    for body in payloads:
        cnpj = buscar_valor(body, ['cnpj'])
        nome = buscar_valor(body, ['institui', 'nome'])
        tipo = buscar_valor(body, ['tipo', 'categoria'], 'Banco/Financeira')
        
        # Usa CNPJ como chave principal; se em branco (conglomerado), usa o Nome
        chave_id = cnpj if cnpj else nome
        if chave_id:
            cursor.execute('''
                INSERT OR REPLACE INTO dim_instituicao (chave_id, nome, segmento)
                VALUES (?, ?, ?)
            ''', (chave_id, nome, tipo))
            
    conn.commit()
    
    # 2. Executa as consultas SQL relacionais para realizar o enriquecimento
    mensagens_processadas = []
    for body in payloads:
        cnpj = buscar_valor(body, ['cnpj'])
        nome = buscar_valor(body, ['institui', 'nome'])
        chave_busca = cnpj if cnpj else nome
        
        cursor.execute("SELECT nome, segmento FROM dim_instituicao WHERE chave_id = ?", (chave_busca,))
        resultado = cursor.fetchone()
        
        if resultado and resultado[0]:
            body['nome_instituicao_enriquecido'] = resultado[0]
            body['segmento_enriquecido'] = resultado[1]
        else:
            body['nome_instituicao_enriquecido'] = nome if nome else 'INSTITUICAO NAO ENCONTRADA'
            body['segmento_enriquecido'] = 'NAO INFORMADO'
            
        mensagens_processadas.append(body)
        
    conn.close()
    
    # 3. Grava o JSON enriquecido no bucket de destino
    arquivo_chave = f"delivery/dados_enriquecidos_{context.aws_request_id}.json"
    s3_client.put_object(
        Bucket=DEST_BUCKET,
        Key=arquivo_chave,
        Body=json.dumps(mensagens_processadas, ensure_ascii=False, indent=2)
    )
    
    return {'status': 200, 'body': f'{len(mensagens_processadas)} registros enriquecidos via SQL'}