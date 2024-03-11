import json
import boto3
import botocore.exceptions
from azure.identity import ClientSecretCredential
from azure.mgmt.network import NetworkManagementClient

def lambda_handler(event, context):
    try:

        print(event)
        # Create a session with the desired region
        session = boto3.session.Session(region_name='us-east-1')
        # Initialize AWS Config client
        config = session.client('config')
        azure_event=json.loads(event['body'])

        # Initialize Azure client variables from os environment
        secret_name = azure_event['SECRETS_MANAGER_AZURE_SECRET_NAME'] # Get AWS Secrets Manager secret name for Azure Client from Lambda event payload
        azure_subscription_id = azure_event['AZURE_SUBSCRIPTION_ID'] # Get Azure Subscription ID from Lambda event payload
        azure_resource_group_name = azure_event['AZURE_RESOURCE_GROUP_NAME']  # Get Azure Resource Group Name from Lambda event payload
        azure_tenant_id = azure_event['AZURE_TENANT_ID']  # Get Azure Tenant ID from Lambda event payload

        # Create a Secrets Manager client
        secretsmanager = session.client('secretsmanager')

        try:
            get_secret_value_response = secretsmanager.get_secret_value(
                SecretId=secret_name
            )
        except botocore.exceptions.ClientError as e:
            # For a list of exceptions thrown, see
            # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
            raise e

        secret = get_secret_value_response['SecretString']
        azure_client_secret = json.loads(secret)['azure_client_secret']
        azure_client_id = json.loads(secret)['azure_client_id']

        credential = ClientSecretCredential(
            tenant_id = azure_tenant_id,
            client_id = azure_client_id,
            client_secret = azure_client_secret
        )

        network_client = NetworkManagementClient(credential, azure_subscription_id)

        group_name = azure_event['GroupName']
        
        security_group = network_client.network_security_groups.get(azure_resource_group_name, group_name)

        # Rename properties from Azure Security Group to match the AWS Config custom resource schema names you created
        security_rules_new_array_of_dictionaries = []
        for rule in security_group.security_rules:
            new_rule = {
                'SecurityRuleId' : rule.id,
                'SecurityRuleName' : rule.name,
                'SecurityRuleType' : rule.type,
                'SecurityRuleProtocol' : rule.protocol, 
                'SecurityRuleSourcePortRange' : rule.source_port_range,
                'SecurityRuleDestinationPortRange' : rule.destination_port_range,
                'SecurityRuleSourceAddressPrefix' : rule.source_address_prefix,
                'SecurityRuleSourceAddressPrefixes' : rule.source_address_prefixes,
                'SecurityRuleDestinationAddressPrefix' : rule.destination_address_prefix,
                'SecurityRuleDestinationAddressPrefixes' : rule.destination_address_prefixes,
                'SecurityRuleSourcePortRanges' : rule.source_port_ranges,
                'SecurityRuleDestinationPortRanges' : rule.destination_port_ranges,
                'SecurityRuleAccess' : rule.access,
                'SecurityRulePriority' : rule.priority,
                'SecurityRuleDirection' : rule.direction,
                'SecurityRuleProvisioningState' : rule.provisioning_state,
            }
            security_rules_new_array_of_dictionaries.append(new_rule)

        # Prepare the AWS Config custom resource configuration item data
        resource_details = {
            'SecurityGroupName': security_group.name,
            'SecurityGroupId': security_group.id,
            'AzureResourceType': security_group.type,
            'SecurityGroupLocation': security_group.location,
            'SecurityGroupTags': security_group.tags,
            'SecurityRules': security_rules_new_array_of_dictionaries
        }

        
        #configurationprint = json.dumps(resource_details)

        # Send the custom resource configuration item data to AWS Config
        config.put_resource_config(
            ResourceType='AzureTest::VM::SecurityGroup',
            ResourceName=resource_details['SecurityGroupName'],
            ResourceId=resource_details['SecurityGroupId'],
            Configuration=json.dumps(resource_details),
            Tags={},
            SchemaVersionId='00000007'
        )

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise e