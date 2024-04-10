import boto3
import os


# Initialize AWS clients
cloudtrail_client = boto3.client('cloudtrail')
sns_client = boto3.client('sns')

# Function to retrieve federated user activity and check for untagged resources
def check_untagged_resources():
    untagged_resources = []

    # Query CloudTrail logs for events related to resource provisioning by federated users
    response = cloudtrail_client.lookup_events(
        LookupAttributes=[
            {
                'AttributeKey': 'EventName',
                'AttributeValue': 'Create*'
            },
            
        ]
    )

    for event in response['Events']:
        # Extract relevant information from the CloudTrail events
        user_id = event['UserIdentity'].get('Arn')
        resource_arn = event['Resources'][0]['ResourceARN']

        # Check if the resource has tags
        tags = get_resource_tags(resource_arn)
        if not tags:
            untagged_resources.append({'arn': resource_arn, 'user_id': user_id})

    return untagged_resources

# Function to retrieve resource tags
def get_resource_tags(resource_arn):
    # Use AWS SDK to get tags for the resource
    
    tags = []

    try:
        resource_type = resource_arn.split(':')[2]
        resource_id = resource_arn.split('/')[-1]

        if resource_type == 's3':
            s3_client = boto3.client('s3')
            response = s3_client.get_bucket_tagging(Bucket=resource_id)
            tags = response.get('TagSet', [])
        elif resource_type == 'ec2':
            ec2_client = boto3.client('ec2')
            response = ec2_client.describe_tags(
                Filters=[
                    {'Name': 'resource-id', 'Values': [resource_id]}
                ]
            )
            tags = response.get('Tags', [])
        # Add more resource types as needed

    except Exception as e:
        print(f"Error getting tags for resource {resource_arn}: {e}")

    return tags

# Function to send notifications for untagged resources
def send_notification(untagged_resources):
    if not untagged_resources:
        return

    notification_message = "The following resources provisioned by Federated IAM users are not properly tagged:\n"
    for resource in untagged_resources:
        notification_message += f"- Resource: {resource['arn']}, User ID: {resource['user_id']}\n"

    # Send notification using AWS SNS
    try:
        sns_client.publish(
            TopicArn='arn:aws:sns:ap-southeast-2:590183937261:xc3team12-notification-topic', 
            Subject='Untagged Resources Notification',
            Message=notification_message
        )
    except Exception as e:
        print(f"Error sending notification: {e}")

# AWS Lambda handler function
def lambda_handler(event, context):
    try:
        # Check for untagged resources
        untagged_resources = check_untagged_resources()

        # If untagged resources are found, send notifications
        send_notification(untagged_resources)

    except Exception as e:
        print(f"Error in lambda_handler: {e}")

