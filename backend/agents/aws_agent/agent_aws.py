#!/usr/bin/env python3
import boto3
import requests
import time
import os
from dotenv import load_dotenv

# Load config
load_dotenv("/opt/ai-incident-agent/.env")
API_URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")
PROJECT_ID = os.getenv("PROJECT_ID")
REGION = os.getenv("AWS_REGION", "us-east-1")

cloudwatch = boto3.client("cloudwatch", region_name=REGION)

def report_incident(message):
    payload = {
        "project_id": PROJECT_ID,
        "category": "aws_cloud",
        "incident": message
    }
    headers = {"x-api-key": API_KEY}
    try:
        r = requests.post(API_URL, json=payload, headers=headers, timeout=10)
        print("Incident sent:", r.json())
    except Exception as e:
        print("Error sending incident:", e)

def check_ec2_cpu(instance_id):
    stats = cloudwatch.get_metric_statistics(
        Namespace="AWS/EC2",
        MetricName="CPUUtilization",
        Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
        StartTime=time.time()-600,
        EndTime=time.time(),
        Period=300,
        Statistics=["Average"]
    )
    datapoints = stats.get("Datapoints", [])
    if datapoints:
        avg = datapoints[-1]["Average"]
        if avg > 80:
            report_incident(f"EC2 {instance_id} high CPU: {avg}%")

while True:
    # Example: take instance IDs from env
    instance_ids = os.getenv("AWS_INSTANCES", "").split(",")
    for instance_id in instance_ids:
        if instance_id.strip():
            check_ec2_cpu(instance_id.strip())
    time.sleep(60)
