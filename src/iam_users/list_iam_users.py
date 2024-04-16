# Copyright (c) 2023, Xgrid Inc, https://xgrid.co

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import io
import gzip
import json
import boto3
import botocore
import os
import logging
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
from urllib.parse import unquote_plus
from datetime import datetime

try:
    s3 = boto3.client("s3")
    bucket_name = os.environ["bucket_name"]
except Exception as e:
    logging.error("Error creating boto3 client: " + str(e))
try:
    sns = boto3.client("sns")
except Exception as e:
    logging.error("Error creating boto3 client: " + str(e))

# Initializing environment variables
runtime_region = 'ap-southeast-2' #os.environ["REGION"]
# topic_arn = os.environ["sns_topic"]

def verify_tags(tags):
    required_tags = ['Owner','Creator', 'Project']
    if all(tag in tags for tag in required_tags):
        return True
    else:
        return False

def get_resources_for_account_id(account_id):
    # Initialize the Resource Groups Tagging API client
    client = boto3.client('resourcegroupstaggingapi')
    
    # Retrieve resources with the specified account ID
    paginator = client.get_paginator('get_resources')
    resources = []
    
    try:
        # Paginate through the list of resources
        for page in paginator.paginate(ResourceTypeFilters=['s3', 'lambda', 'ec2:instance']):
            for resource in page.get('ResourceTagMappingList', []):
                resource_arn = resource['ResourceARN']
                
                tags = {tag['Key']: tag['Value'] for tag in resource.get('Tags', [])}
                
                resources.append({'ResourceARN': resource_arn, 'Tags': tags, 'Compliance': verify_tags(tags)})
                # resources.append({'ResourceARN': resource_arn, 'Tags': tags})
                # Check resource type and add to appropriate list
                # if verifyTags(tags):
                    # if resource_arn.startswith('arn:aws:s3:'):
                    #     resources.append({'ResourceARN': resource_arn, 'tags': tags})
                    # elif resource_arn.startswith('arn:aws:lambda:'):
                    #     resources.append({'ResourceARN': resource_arn, 'tags': tags})
                    # elif resource_arn.startswith('arn:aws:ec2:'):
                    #     resources.append({'ResourceARN': resource_arn, 'tags': tags})
    except Exception as e:
        print(f"Error retrieving resources: {str(e)}")
    
    return resources

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
    
    # Convert the set of account IDs to a list
    accounts = list(account_ids)
    # Process or format user information
    # Process or format user information
    # formatted_users = []
    # counter = 0
    # for user in users:
    #     counter = counter + 1
    #     formatted_users.append(
        
    #         {'user'+str(counter) :
    #             {
    #                 'UserName' : user['UserName'],
    #                 'userid': user['UserId'],
    #                 'arn' : user['Arn'],
    #                 'token': sts_client.get_federation_token(
    #                     Name= user['UserName'],  # Specify the name for the federated user
    #                     DurationSeconds=3600  # Specify the duration for which the credentials are valid
    #                 )['FederatedUser']['FederatedUserId']
    #             }
    #         }
    #     )
    # Return the formatted user information
    all_resources = {}
    for account_id in account_ids:
        resources = get_resources_for_account_id(account_id)
        all_resources.update({account_id:resources})
        
    current_date = datetime.now()
    year = str(current_date.year)
    month = current_date.strftime('%m')
    day = current_date.strftime('%d')

    # Set the destination key
    # bucket = event["Records"][0]["s3"]["bucket"]["name"]
    destination_key = f"fed-resources/{year}/{month}/{day}/resources.json"
    try:
        s3.put_object(Bucket=bucket_name, Key=destination_key, Body=json.dumps({'body':all_resources}))
    except botocore.exceptions.ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchBucket":
            raise ValueError(f"Bucket not found: {os.environ['bucket_name']}")
        elif e.response["Error"]["Code"] == "AccessDenied":
            raise ValueError(
                f"Access denied to S3 bucket: {os.environ['bucket_name']}"
            )
        else:
            raise ValueError(f"Failed to upload data to S3 bucket: {str(e)}")
    
    return {
        'statusCode': 200,
        'body': all_resources
    }
    # account_id = context.invoked_function_arn.split(":")[4]
    # user_detail_data = []
    # iam_user_detail = []
    # # Getting IAM User Detail from S3 bucket
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    # key = unquote_plus(event["Records"][0]["s3"]["object"]["key"])
    # # parsing resource.json file
    # if "resources" in key:
    #     try:
    #         response = s3.get_object(Bucket=bucket, Key=key)
    #         resource_file = response["Body"].read()
    #         with gzip.GzipFile(fileobj=io.BytesIO(resource_file), mode="rb") as data:
    #             user_detail_data = json.load(data)
    #     except Exception as e:
    #         logging.error(
    #             """
    #             Error getting object {} from bucket {}.
    #             Make sure bucket and function are in the same region.
    #             """.format(
    #                 key, bucket
    #             ),
    #             str(e),
    #         )
    #         return {"statusCode": 500, "body": json.dumps({"Error": str(e)})}
    # logging.info(user_detail_data)
    # if len(user_detail_data) == 0:
    #     return {"statusCode": 200, "body": json.dumps("IAM Users don't exist")}
    # # Initialize the Prometheus registry and gauge
    # else:
    #     try:
    #         registry = CollectorRegistry()
    #         g_user = Gauge(
    #             "IAM_Users",
    #             "IAM Users",
    #             labelnames=["user_name", "user_arn", "user_id", "account_id"],
    #             registry=registry,
    #         )
    #         for iterator in range(len(user_detail_data)):
    #             user_name = user_detail_data[iterator]["UserName"]
    #             user_arn = user_detail_data[iterator]["Arn"]
    #             user_id = user_detail_data[iterator]["UserId"]
    #             user_info = {
    #                 "UserName": user_name,
    #                 "UserArn": user_arn,
    #                 "UserId": user_id,
    #             }
    #             # Add the IAM User detail to the gauge
    #             g_user.labels(user_name, user_arn, user_id, account_id).set(0)
    #             iam_user_detail.append(user_info)
    #         # Push the gauge data to Prometheus
    #         push_to_gateway(
    #             os.environ["prometheus_ip"], job="IAM_User_Details", registry=registry
    #         )
    #     except Exception as e:
    #         logging.error("Error initializing Prometheus Registry and Gauge: " + str(e))
    #         return {"statusCode": 500, "body": json.dumps({"Error": str(e)})}
    #     # message for SNS Topic
    #     payload_data = iam_user_detail
    #     try:
    #         sns.publish(
    #             TopicArn=topic_arn,
    #             Message=json.dumps({"default": json.dumps(payload_data)}),
    #             MessageStructure="json",
    #         )
    #     except Exception as e:
    #         logging.error("Error in publish SNS message: " + str(e))
    #         return {"statusCode": 500, "body": json.dumps({"Error": str(e)})}

    # return {"statusCode": 200, "body": json.dumps(iam_user_detail)}