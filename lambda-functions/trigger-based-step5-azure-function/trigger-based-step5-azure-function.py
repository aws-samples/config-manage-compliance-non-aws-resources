import logging
from typing import List
import azure.functions as func
import requests
import json
import os
from requests_aws4auth import AWS4Auth

def main(events: List[func.EventHubEvent]):

    for event in events:
        #logging.info('Event Hub raw event: %s', event)
        event_data = event.get_body()
        my_json = event_data.decode('utf-8')
        data = json.loads(my_json)
        logging.info('Data event: %s', data)
        logging.info('Data event record 0: %s', data['records'][0])
        resourceId= data['records'][0]['resourceId']
        operationName = data['records'][0]['operationName']
        resultType = data['records'][0]['resultType']
        resourceDelimited = resourceId.split("/")
        resourceIdType = resourceDelimited[7]
        logging.info(f'ResourceId Type: {resourceIdType}')
        logging.info(f'Operation Name: {operationName}')
        logging.info(f'Result Type: {resultType}')
        if (resourceIdType == 'NETWORKSECURITYGROUPS' and resultType == 'Success'):
            subscriptionId= resourceDelimited[2]
            resourceGroupName = resourceDelimited[4]
            resourceName = resourceDelimited[8]
            send_to_aws(resourceName, resourceGroupName, subscriptionId)
            logging.info('Event Hub message body: %s', event.get_body().decode('utf-8'))
        
# Process the Azure Network Security Group log event here    
def send_to_aws(resourceName,resourceGroupName, subscriptionId):
    logging.info('AWS Access Key: %s', os.environ.get('aws_access'))
    # Create a signed AWS request
    region = 'us-east-1'
    service = 'lambda'
    access_id = os.environ.get('aws_access')
    access_secret = os.environ.get('aws_secret')
    awsauth = AWS4Auth(access_id, access_secret, region, service)
    # Define the AWS Lambda function url that will process the Azure Network Security Group log event to add into AWS Config. Replace this with your AWS Lambda Function URL.
    url = 'https://YOUR-AWS-LAMBDA-FUNCTION-URL.lambda-url.us-east-1.on.aws/'
    # Define the JSON payload.
    payload = {
        "GroupName": resourceName,
        #Replace with your AWS Secrets Manager secret name that has your Azure secret for connecting to.
        "SECRETS_MANAGER_AZURE_SECRET_NAME": "REPLACE-WITH-YOUR-AWS-SECRETS-MANAGER-SECRET-NAME",
        "AZURE_SUBSCRIPTION_ID": subscriptionId,
        "AZURE_RESOURCE_GROUP_NAME": resourceGroupName,
        #Replace with your Azure Tenant ID
        "AZURE_TENANT_ID": "REPLACE-WITH-YOUR-AZURE-TENANT-ID"
    }
    # Send the POST request with JSON payload
    headers = {'Content-Type': 'application/json'}
    response = requests.post(url, auth=awsauth, data=json.dumps(payload), headers=headers)
    # Print the response
    logging.info(response.text)
    logging.info(f'Status code: {response.status_code}')
    logging.info('Response content:')
    logging.info(response.content)