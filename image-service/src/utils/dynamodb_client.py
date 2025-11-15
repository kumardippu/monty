"""Simple DynamoDB client for storing image metadata."""
import boto3
import os
import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

class DynamoDBClient:
    """Handles DynamoDB operations for image metadata."""
    
    def __init__(self, table_name: str):
        """Initialize DynamoDB client.
        
        Args:
            table_name: Name of the DynamoDB table (e.g., 'image-metadata')
        """
        self.table_name = table_name
        # Connect to LocalStack or real AWS
        endpoint = os.getenv('DYNAMODB_ENDPOINT_URL', 'http://localhost:4566')
        self.dynamodb_client = boto3.client(
            'dynamodb',
            endpoint_url=endpoint,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        dynamodb = boto3.resource(
            'dynamodb',
            endpoint_url=endpoint,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self.table = dynamodb.Table(table_name)
        # Auto-create table if it doesn't exist (for LocalStack)
        self._ensure_table_exists()
    
    def _ensure_table_exists(self):
        """Create table if it doesn't exist (only for LocalStack)."""
        try:
            # Check if table exists
            self.dynamodb_client.describe_table(TableName=self.table_name)
        except Exception:
            # Table doesn't exist, create it (only if using LocalStack)
            endpoint = os.getenv('DYNAMODB_ENDPOINT_URL', '')
            if 'localhost' in endpoint or '127.0.0.1' in endpoint:
                try:
                    self.dynamodb_client.create_table(
                        TableName=self.table_name,
                        KeySchema=[{'AttributeName': 'image_id', 'KeyType': 'HASH'}],
                        AttributeDefinitions=[{'AttributeName': 'image_id', 'AttributeType': 'S'}],
                        BillingMode='PAY_PER_REQUEST'
                    )
                    # Wait for table to be ready
                    waiter = self.dynamodb_client.get_waiter('table_exists')
                    waiter.wait(TableName=self.table_name)
                except Exception as e:
                    if 'ResourceInUseException' not in str(e):
                        # Ignore if already exists, but log other errors
                        pass
    
    def save_metadata(self, image_id: str, user_id: str, filename: str, 
                     s3_key: str, content_type: str, size: int, 
                     metadata: Optional[Dict] = None) -> Dict:
        """Save image metadata to DynamoDB.
        
        Args:
            image_id: Unique ID for the image
            user_id: ID of the user who uploaded it
            filename: Original filename
            s3_key: Path in S3 where image is stored
            content_type: Image type (e.g., 'image/jpeg')
            size: File size in bytes
            metadata: Optional extra information (dict)
            
        Returns:
            The saved metadata record
        """
        item = {
            'image_id': image_id,
            'user_id': user_id,
            'filename': filename,
            's3_key': s3_key,
            'content_type': content_type,
            'size': size,
            'created_at': datetime.utcnow().isoformat()
        }
        
        if metadata:
            item['metadata'] = json.dumps(metadata)
        
        self.table.put_item(Item=item)
        return item
    
    def get_metadata(self, image_id: str) -> Optional[Dict]:
        """Get image metadata by ID.
        
        Args:
            image_id: The image ID to look up
            
        Returns:
            Metadata dictionary or None if not found
        """
        response = self.table.get_item(Key={'image_id': image_id})
        if 'Item' in response:
            item = response['Item']
            # Convert Decimal to int/float
            for key, value in item.items():
                if isinstance(value, Decimal):
                    item[key] = int(value) if value % 1 == 0 else float(value)
            # Parse metadata JSON string
            if 'metadata' in item and isinstance(item['metadata'], str):
                item['metadata'] = json.loads(item['metadata'])
            return item
        return None
    
    def list_images(self, user_id: Optional[str] = None, 
                   content_type: Optional[str] = None, 
                   limit: int = 100) -> List[Dict]:
        """List all images with optional filters.
        
        Args:
            user_id: Filter by user ID (optional)
            content_type: Filter by content type like 'image/jpeg' (optional)
            limit: Maximum number of results (default: 100)
            
        Returns:
            List of image metadata dictionaries
        """
        # Scan the table
        response = self.table.scan(Limit=limit)
        images = response.get('Items', [])
        
        # Apply filters
        if user_id:
            images = [img for img in images if img.get('user_id') == user_id]
        if content_type:
            images = [img for img in images if img.get('content_type') == content_type]
        
        # Convert Decimal types and parse metadata
        for img in images:
            for key, value in img.items():
                if isinstance(value, Decimal):
                    img[key] = int(value) if value % 1 == 0 else float(value)
            if 'metadata' in img and isinstance(img['metadata'], str):
                img['metadata'] = json.loads(img['metadata'])
        
        return images[:limit]
    
    def delete_metadata(self, image_id: str):
        """Delete image metadata from DynamoDB.
        
        Args:
            image_id: The image ID to delete
        """
        self.table.delete_item(Key={'image_id': image_id})

