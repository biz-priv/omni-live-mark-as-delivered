"""
* File: src\mark-as-delivered.py
* Project: Omni-live-mark-as-delivered
* Author: Bizcloud Experts
* Date: 2021-04-21
* Confidential and Proprietary
"""
import requests
import json
from datetime import datetime, timedelta
import pytz
import time
import pickle
import os
import boto3

def send_sns_notification(message, subject):
    sns_client = boto3.client('sns')
    topic_arn = os.environ['TopicArn']
    sns_client.publish(
        Subject=subject,
        TopicArn=topic_arn,
        Message=message
    )

def lambda_handler(event, context):
    try:
        print("event:", event)   
        for item in event["Payload"]:
            order_id = item['item']["order_id"]
            movement_id = item['item']["movement_id"]
            print("movement id & order id & env :", movement_id, order_id, os.environ['Environment'])
            response = update_movement(movement_id, order_id)
            # Update status based on response
            if response == 200:
                status = 'Accepted'
            else:
                status = 'Rejected'
            # Store data in DynamoDB
            dynamodb = boto3.resource('dynamodb')
            table = dynamodb.Table(os.environ['Dynamo_Table'])
            table.put_item(
                Item={
                    'order_id': order_id,
                    'movement_id': movement_id,
                    'status_code': response
                }
            )
            print("Status:", status)
        return {
            'statusCode': 200,
            'body': json.dumps('Succeeded')
        }
    except Exception as e:
        error_message = f"An error occurred in Lambda function: {str(e)}"
        print(error_message)
        send_sns_notification(error_message, "Error in Lambda Function")
        return {
            'statusCode': 500,
            'body': json.dumps("Internal Error.")
        }



def update_movement(movement_id, order_id):
    ##############
    # GET MOVEMENT INFO
    ##############
    username = os.environ['Username']
    password = os.environ['Password']
    env=os.environ['Environment']
    mcleod_headers = {'Accept': 'application/json',
                      'Content-Type': 'application/json'}
    if env=='dev':
        get_url = f"https://tms-lvlp.loadtracking.com:6790/ws/movement/{movement_id}"
    else:
        get_url = f"https://tms-lvlp.loadtracking.com/ws/movement/{movement_id}"
    get_response = requests.get(get_url, auth=(username, password), headers=mcleod_headers)
    print("55",get_response)
    get_output = get_response.json()
    ##############
    # UPDATE FIELDS (NEED TO UPDATE STOP, ORDER AS WELL, SO GET THE STOP)
    ##############
    dest_stop_id = get_output["dest_stop_id"]
    get_output.pop("brokerage_status_row")
    get_output["brokerage_status"] = "DELIVERD"
    get_output["status"] = "D"
    if env=='dev':
        get_url2 = f"https://tms-lvlp.loadtracking.com:6790/ws/stop/{dest_stop_id}"
    else:
        get_url2 = f"https://tms-lvlp.loadtracking.com/ws/stop/{dest_stop_id}"
    get_response2 = requests.get(get_url2, auth=(username, password), headers=mcleod_headers)
    get_output2 = get_response2.json()
    if env=='dev':
        get_url3 = f"https://tms-lvlp.loadtracking.com:6790/ws/orders/{order_id}"
    else:
        get_url3 = f"https://tms-lvlp.loadtracking.com/ws/orders/{order_id}"
    get_response3 = requests.get(get_url3, auth=(username, password), headers=mcleod_headers)
    get_output3 = get_response3.json()
    get_output3.pop("__statusDescr")
    get_output3['status'] = "D"
    if env=='dev':
        put_url3 = f"https://tms-lvlp.loadtracking.com:6790/ws/orders/update"
    else:
        put_url3 = f"https://tms-lvlp.loadtracking.com/ws/orders/update"
    put_response3 = requests.put(put_url3, auth=(username, password), headers=mcleod_headers, json=get_output3)
    print(f"Updating Order: {put_response3.status_code}")
    arrival = get_output2['actual_arrival']
    arrival = datetime.strptime(arrival, '%Y%m%d%H%M%S%z')
    departure = arrival + timedelta(hours=2)
    departure = departure.strftime('%Y%m%d%H%M%S%z')
    get_output2["actual_departure"] = departure
    get_output2["status"] = "D"
    if env=='dev':
        put_url2 = f"https://tms-lvlp.loadtracking.com:6790/ws/stop/update"
    else:
        put_url2 = f"https://tms-lvlp.loadtracking.com/ws/stop/update"
    put_response2 = requests.put(put_url2, auth=(username, password), headers=mcleod_headers, json=get_output2)
    print(f"Updating Stop: {put_response2.status_code}")
    if env=='dev':
        put_url = f"https://tms-lvlp.loadtracking.com:6790/ws/movement/update"
    else:
        put_url = f"https://tms-lvlp.loadtracking.com/ws/movement/update"
    put_response = requests.put(put_url, auth=(username, password), headers=mcleod_headers, json=get_output)
    print(f"Updating Movement: {put_response.status_code}")
    return put_response.status_code