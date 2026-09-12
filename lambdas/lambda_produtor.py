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
        # Decodificação em latin1 para aceitar acentuação em português
        content = response['Body'].read().decode('latin1')
        
        csv_file = StringIO(content)
        reader = csv.DictReader(csv_file, delimiter=';')
        
        for row in reader:
            sqs_client.send_message(
                QueueUrl=SQS_QUEUE_URL,
                MessageBody=json.dumps(row, ensure_ascii=False)
            )
            
    return {'status': 200, 'message': 'Eventos enviados para a fila com sucesso'}