"""Simple script to set up LocalStack - Creates S3 bucket and DynamoDB table."""
import boto3
import os
import sys
import time

# LocalStack settings
ENDPOINT = 'http://localhost:4566'
REGION = 'us-east-1'

def check_localstack():
    """Check if LocalStack is running."""
    try:
        import requests
        response = requests.get(f'{ENDPOINT}/_localstack/health', timeout=2)
        if response.status_code == 200:
            return True
    except:
        pass
    return False

def create_s3_bucket():
    """Create S3 bucket for storing images."""
    s3 = boto3.client(
        's3',
        endpoint_url=ENDPOINT,
        aws_access_key_id='test',
        aws_secret_access_key='test',
        region_name=REGION
    )
    
    bucket_name = 'images'
    
    try:
        s3.create_bucket(Bucket=bucket_name)
        print(f"Created S3 bucket: {bucket_name}")
    except Exception as e:
        if 'BucketAlreadyExists' in str(e) or 'BucketAlreadyOwnedByYou' in str(e):
            print(f"S3 bucket already exists: {bucket_name}")
        else:
            print(f"Error creating bucket: {e}")
            raise

def create_dynamodb_table():
    """Create DynamoDB table for storing image metadata."""
    dynamodb = boto3.client(
        'dynamodb',
        endpoint_url=ENDPOINT,
        aws_access_key_id='test',
        aws_secret_access_key='test',
        region_name=REGION
    )
    
    table_name = 'image-metadata'
    
    try:
        dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {'AttributeName': 'image_id', 'KeyType': 'HASH'}
            ],
            AttributeDefinitions=[
                {'AttributeName': 'image_id', 'AttributeType': 'S'}
            ],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Wait for table to be ready
        print("Waiting for table to be ready...")
        waiter = dynamodb.get_waiter('table_exists')
        waiter.wait(TableName=table_name)
        print(f"Created DynamoDB table: {table_name}")
        
    except Exception as e:
        if 'ResourceInUseException' in str(e):
            print(f"DynamoDB table already exists: {table_name}")
        else:
            print(f"Error creating table: {e}")
            raise

def main():
    """Main function - sets up everything."""
    print("Setting up LocalStack...")
    print(f"Endpoint: {ENDPOINT}\n")
    
    # Check if LocalStack is running
    if not check_localstack():
        print("Error: LocalStack is not running")
        print("Start it with: docker-compose up -d")
        print("Then wait 10 seconds and run this script again.")
        return 1
    
    print("LocalStack is running\n")
    
    try:
        create_s3_bucket()
        create_dynamodb_table()
        print("\nSetup complete!")
        print("You can now upload images.")
    except Exception as e:
        print(f"\nSetup failed: {e}")
        print("\nMake sure:")
        print("  1. LocalStack is running: docker-compose up -d")
        print("  2. boto3 is installed: pip install boto3")
        return 1
    
    return 0

if __name__ == '__main__':
    exit(main())

