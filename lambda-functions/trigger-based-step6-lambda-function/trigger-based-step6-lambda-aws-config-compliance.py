import json
import boto3
from datetime import datetime



def lambda_handler(event, context):
    # Parse the invoking event string as JSON
    invoking_event = json.loads(event['invokingEvent'])

    try:
        # Initialize AWS Config client
        config = boto3.client('config')

        # Get properties from the event
        group_name = invoking_event['configurationItem']['resourceId']

        # Get configuration history for the Azure Security Group
        response = config.get_resource_config_history(
            resourceType='AzureTest::VM::SecurityGroup',
            resourceId=group_name
        )

        # Get the most recent configuration
        current_config = json.loads(response['configurationItems'][0]['configuration'])

        # Check the security group's rules
        for rule in current_config['SecurityRules']:
            if (rule['SecurityRuleDestinationPortRange'] == '22' and (rule['SecurityRuleSourceAddressPrefix'] == '*' or rule['SecurityRuleSourceAddressPrefix'] == '0.0.0.0/0') and 
                rule['SecurityRuleAccess'] == 'Allow' and rule['SecurityRuleDirection'] == 'Inbound'):
                # If the rule matches, the resource is not compliant
                config.put_evaluations(
                    Evaluations=[
                        {
                            'ComplianceResourceType': invoking_event['configurationItem']['resourceType'],
                            'ComplianceResourceId': group_name,
                            'ComplianceType': 'NON_COMPLIANT',
                            'Annotation': 'The security group contains a rule that allows ingress from * (any) to port 22.',
                            'OrderingTimestamp': datetime.now()
                        }
                    ],
                    ResultToken=event['resultToken']
                )
                return

        # If no matching rule was found, the resource is compliant
        config.put_evaluations(
            Evaluations=[
                {
                    'ComplianceResourceType': invoking_event['configurationItem']['resourceType'],
                    'ComplianceResourceId': group_name,
                    'ComplianceType': 'COMPLIANT',
                    'Annotation': 'The security group does not contain any rules that allow ingress from * (any) to port 22.',
                    'OrderingTimestamp': datetime.now()
                }
            ],
            ResultToken=event['resultToken']
        )

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise e