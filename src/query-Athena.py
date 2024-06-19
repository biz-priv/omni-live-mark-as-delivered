"""
* File: src\query-Athena.py
* Project: Omni-live-mark-as-delivered
* Author: Bizcloud Experts
* Date: 2021-04-21
* Confidential and Proprietary
"""
import json
import csv 
import boto3
import time
import os

def send_sns_notification(message, subject):
    sns_client = boto3.client('sns')
    topic_arn = os.environ['TopicArn']
    sns_client.publish(
        Subject=subject,
        TopicArn=topic_arn,
        Message=message
    )

def read_query_from_file(file_path):
    with open(file_path, 'r') as file:
        query_string = file.read()
    return query_string

def lambda_handler(event, context):
    try:
        print("event:", event)
        athena = boto3.client('athena')
        ssm = boto3.client('ssm')
        query_file_path = 'src/query_file.sql'
        query_string = read_query_from_file(query_file_path)
        env = os.environ['Environment']
        if env == 'dev':
            database = 'dw-etl-lvlp-dev'
        else:
            database = 'dw-etl-lvlp-prod'
        query_execution = athena.start_query_execution(
            QueryString=query_string,
            QueryExecutionContext={'Database': database}
        )
        query_execution_id = query_execution['QueryExecutionId']
        while True:
            query_status = athena.get_query_execution(QueryExecutionId=query_execution_id)
            state = query_status['QueryExecution']['Status']['State']
            if state == 'QUEUED':
                print("queued", query_status)
                time.sleep(3)
            elif state == 'SUCCEEDED':
                print("Succeeded", query_status)
                query_results = athena.get_query_execution(QueryExecutionId=query_execution_id)
                s3_file_path = query_results['QueryExecution']['ResultConfiguration']['OutputLocation']
                print("S3 Path:", query_results['QueryExecution']['ResultConfiguration']['OutputLocation'])
                s3_bucket = s3_file_path.split('/', 3)[-2]
                s3_key = s3_file_path.split('/', 3)[-1]

                # Send the S3 key to an SSM parameter
                # parameter_name = os.environ['ssm_parameter'] # Specify your SSM parameter name
                # ssm.put_parameter(
                #     Name=parameter_name,
                #     Value=s3_key,
                #     Type='String',
                #     Overwrite=True  # Overwrite if parameter exists
                # )
                # print("S3 Key sent to SSM parameter:", parameter_name)

                break  # Exit the loop after sending the parameter

        return {"Bucket": s3_bucket, "Key": s3_key}
    except Exception as e:
        error_message = f"An error occurred in Lambda function: {str(e)}"
        print(error_message)
        send_sns_notification(error_message, "Error in Lambda Function")
        return {"statusCode": 500, "body": json.dumps("Internal Error.")}
