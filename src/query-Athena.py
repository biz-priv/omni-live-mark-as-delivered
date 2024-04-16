import json
import csv 
import boto3
import time
import os

def read_query_from_file(file_path):
    with open(file_path, 'r') as file:
        query_string = file.read()
    return query_string

def lambda_handler(event, context):
    print("event:",event)
    
    athena = boto3.client('athena')
    ssm = boto3.client('ssm')
    query_file_path = 'src/query_file.sql'
    query_string = read_query_from_file(query_file_path)
    query_execution = athena.start_query_execution(
        QueryString= query_string, #"select distinct o.id as order_id,s1.actual_departure, o.status,mo.num_of_moves,m.brokerage_status,o.shipper_stop_id , o.consignee_stop_id,date_diff('hour', s1.actual_departure, CURRENT_DATE) as date_diff_hrs, o.ready_to_bill from orders o left join stop s1 on s1.id =o.shipper_stop_id left join stop s2 on s2.id =o.consignee_stop_id left join (select o.id, count (mo.movement_id) as num_of_moves from orders o left join movement_order mo on mo.order_id = o.id group by o.id) mo on mo.id=o.id left join movement_order mo2 on mo2.order_id =o.id left join movement m on m.id = mo2.movement_id where o.status = 'D' and o.ready_to_bill='N' and mo.num_of_moves=1 and m.brokerage_status='DELIVERD' and date_diff('hour', s1.actual_departure, CURRENT_DATE) >= 96 limit 10;",
        QueryExecutionContext={
            'Database':  'ready-to-bill-db' 
        }
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
            parameter_name = os.environ['ssm_parameter'] # Specify your SSM parameter name
            ssm.put_parameter(
                Name=parameter_name,
                Value=s3_key,
                Type='String',
                Overwrite=True  # Overwrite if parameter exists
            )
            print("S3 Key sent to SSM parameter:", parameter_name)
            break  # Exit the loop after sending the parameter
            
    return {"Bucket": s3_bucket,"Key":s3_key}