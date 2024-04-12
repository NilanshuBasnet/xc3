from prometheus_client import CollectorRegistry, Gauge, push_to_gateway
from random import randint

# Create a registry to collect your metrics
registry = CollectorRegistry()

# Define your metrics
ec2_cost = Gauge('aws_service_ec2_cost', 'Dummy EC2 cost', ['user'], registry=registry)
lambda_cost = Gauge('aws_service_lambda_cost', 'Dummy Lambda cost', ['user'], registry=registry)

# Generate dummy data for users
users = ['Alice', 'Bob', 'Charlie', 'David']
for user in users:
    ec2_cost.labels(user=user).set(randint(100, 200))  # Random cost between 100 and 200
    lambda_cost.labels(user=user).set(randint(50, 100))  # Random cost between 50 and 100

# Push the metrics to Pushgateway
push_to_gateway('localhost:9091', job='aws_costs_dummy', registry=registry)
