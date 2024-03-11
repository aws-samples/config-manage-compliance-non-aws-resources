import json
import boto3
import os
import logging
from azure.storage.blob import BlobServiceClient

# Configure the logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

def lambda_handler(event, context):
    try:
        # Add an environment variable to your AWS Lambda named CONNECT_STR so that the Lambda can connect to your Azure Storage account and retrieve the Azure Blob data.
        connect_str = os.getenv('CONNECT_STR')
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        # Get a client to interact with your specified Azure Blob Storage container.
        container_client = blob_service_client.get_container_client("REPLACE-WITH-YOUR-AZURE-BLOB-STORAGE-CONTAINER")
        
        blobs = container_client.list_blobs()
        resource_configuration = {}
        
        # Create a session with your desired AWS region
        session = boto3.session.Session(region_name='us-east-1')
        # Initialize AWS Config client in your chosen AWS region
        config = session.client('config')

        for blob in blobs:
            logger.info(f"Processing blob: {blob.name}")
            resource_configuration = {
                'BlobName': blob.name,
                'ServerSideEncryption': blob.server_encrypted,
            }
            
            # Put the resource configuration in AWS Config
            config.put_resource_config(
                ResourceType='Azure::Blob::Encryption',
                ResourceName=blob.name,
                ResourceId=resource_configuration['BlobName'],
                Configuration=json.dumps(resource_configuration),
                Tags={},
                SchemaVersionId='00000001'
            )
        
        # Return a success message
        return {
            'statusCode': 200,
            'body': json.dumps('Successfully processed the Azure blob data and updated the AWS Config resource.')
        }
    
    except Exception as e:
        # Log the error
        logger.error("An error occurred: %s", str(e))
        # Return an error response
        return {
            'statusCode': 500,
            'body': json.dumps('Error processing the Azure blob data')
        }
