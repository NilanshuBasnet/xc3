import json
import os
import logging
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

# Function to push metrics for federated IAM users with tagged resources to Prometheus
def push_metrics_to_prometheus(data, registry):
    # Gauges for each type of cost
    ec2_gauge = Gauge('ec2_cost', 'Cost incurred by EC2 service', ['IAM_User'], registry=registry)
    lambda_gauge = Gauge('lambda_cost', 'Cost incurred by Lambda service', ['IAM_User'], registry=registry)
    s3_gauge = Gauge('s3_cost', 'Cost incurred by S3 service', ['IAM_User'], registry=registry)
    total_cost_gauge = Gauge('total_cost', 'Total cost incurred by user', ['IAM_User'], registry=registry)
    
    # Loop over each user in the data
    for user in data:
        iam_user = user['userIdentity']['sessionContext']['sessionIssuer']['userName']
        if 'Tagged' in user['userIdentity']:  # Check if the resources are tagged
            ec2_cost = user['userIdentity']['serviceCosts']['EC2']
            lambda_cost = user['userIdentity']['serviceCosts']['Lambda']
            s3_cost = user['userIdentity']['serviceCosts']['S3']
            total_cost = user['userIdentity']['serviceCosts']['TotalCost']
            
            ec2_gauge.labels(iam_user).set(ec2_cost)
            lambda_gauge.labels(iam_user).set(lambda_cost)
            s3_gauge.labels(iam_user).set(s3_cost)
            total_cost_gauge.labels(iam_user).set(total_cost)

            try:
                # Push the metrics to Prometheus Pushgateway using the IP defined in 'prometheus_ip' environment variable
                push_to_gateway(
                    os.environ['prometheus_ip'],
                    job='aws_cost_metrics',
                    registry=registry
                )
            except Exception as e:
                raise ValueError(f"Failed to push cost data to Prometheus: {str(e)}")

# Load your dummy data
with open('dummy_data.json', 'r') as file:
    dummy_data = json.load(file)

registry = CollectorRegistry()
# Call the function to push data to Prometheus
push_metrics_to_prometheus(dummy_data, registry)
