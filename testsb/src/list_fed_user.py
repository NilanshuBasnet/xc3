import io
import gzip
import json
import boto3
import os
import logging

try:
    s3 = boto3.client("s3")
except Exception as e:
    logging.error("Error creating boto3 client: " + str(e))
try:
    sns = boto3.client("sns")
except Exception as e:
    logging.error("Error creating boto3 client: " + str(e))

# Initializing environment variables
runtime_region = os.environ["region"]

def get_resources_for_account_id(account_id):
    # Initialize the Resource Groups Tagging API client
    client = boto3.client('resourcegroupstaggingapi')
    
    # Retrieve resources with the specified account ID
    paginator = client.get_paginator('get_resources')
    resources = []
    
    try:
        # Paginate through the list of resources
        for page in paginator.paginate(ResourceTypeFilters=['ec2','lambda','s3']):
            for resource in page.get('ResourceTagMappingList', []):
                if resource.get('ResourceARN', '').startswith(f'arn:aws:'):
                    if account_id in resource.get('ResourceARN'):
                        resources.append(resource.get('ResourceARN'))
    except Exception as e:
        print(f"Error retrieving resources: {str(e)}")
    
    return paginator.paginate()

def lambda_handler(event, context):
    """
    List IAM User Details.
    Args:
        Account ID: AWS account id.
    Returns:
        It returns a list of IAM Users details in provided aws account.
    Raises:
        Lambda Invoke Error: Raise error if message doesn't publish in SNS topic
    """

    # Initialize IAM client
    iam = boto3.client('iam')
    sts_client = boto3.client('sts')
    
    # Call list_users method
    
    # response = iam.list_groups()
    
    # Extract user information from the response
    # users = response['Users']
    response = iam.list_roles()
    account_ids = set()
    # Process the response
    for role in response.get('Roles', []):
        assume_role_policy_document = role.get('AssumeRolePolicyDocument', {})
        principal = assume_role_policy_document.get('Statement', [{}])[0].get('Principal', {})
        federated_value = principal.get('Federated')
        if federated_value:
            # Extract the account ID from the federated ARN
            account_id = federated_value.split(':')[4]
            account_ids.add(account_id)

 # Return the formatted user information
    all_resources = []
    for account_id in account_ids:
        resources = get_resources_for_account_id(account_id)
        all_resources.extend(resources)
    
    return {
        'statusCode': 200,
        'body': {'all_resources': all_resources }
    }           