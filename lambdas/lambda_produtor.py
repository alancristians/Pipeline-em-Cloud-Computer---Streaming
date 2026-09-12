import json
import boto3
import os
import csv
from io import StringIO

s3_client = boto3.client('s3')
sqs_client = boto3.client('sqs')
SQS_QUEUE_URL = os.environ['SQS_QUEUE_URL']

def lambda_handler(event, context):
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        response = s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('latin1')
        
        csv_file = StringIO(content)
        reader = csv.DictReader(csv_file, delimiter=';')
        
        entries = []
        for i, row in enumerate(reader):
            entries.append({
                'Id': str(i),
                'MessageBody': json.dumps(row, ensure_ascii=False)
            })
            
            # Envia em lotes de 10 mensagens
            if len(entries) == 10:
                sqs_client.send_message_batch(
                    QueueUrl=SQS_QUEUE_URL,
                    Entries=entries
                )
                entries = []
        
        # Envia o restante caso a contagem final não seja múltiplo de 10
        if entries:
            sqs_client.send_message_batch(
                QueueUrl=SQS_QUEUE_URL,
                Entries=entries
            )
            
    return {'status': 200, 'message': 'Eventos enviados em lote para a fila com sucesso'}