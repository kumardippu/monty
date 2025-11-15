"""Lambda function: View or download image."""
import json
import base64
from typing import Dict, Any

from utils.s3_client import S3Client
from utils.dynamodb_client import DynamoDBClient

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """View or download an image.
    
    What it does:
    1. Gets image ID from URL path
    2. Gets image metadata from DynamoDB
    3. If download=true: returns presigned URL
    4. If download=false: returns image data directly
    
    Expected request:
    {
        "pathParameters": {
            "image_id": "uuid-here"
        },
        "queryStringParameters": {
            "download": "true"  // Optional: get URL instead of image
        }
    }
    """
    try:
        # Step 1: Get image ID from URL
        path_params = event.get('pathParameters') or {}
        image_id = path_params.get('image_id')
        
        if not image_id:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Image ID is required'})
            }
        
        # Step 2: Get metadata from DynamoDB
        db_client = DynamoDBClient(table_name='image-metadata')
        metadata = db_client.get_metadata(image_id)
        
        if not metadata:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Image not found'})
            }
        
        # Step 3: Check if user wants download URL or image data
        query_params = event.get('queryStringParameters') or {}
        download = query_params.get('download', 'false').lower() == 'true'
        
        s3_client = S3Client(bucket_name='images')
        
        if download:
            # Step 4a: Return presigned URL (temporary download link)
            presigned_url = s3_client.get_presigned_url(
                key=metadata['s3_key'],
                expires_in=3600  # 1 hour
            )
            return {
                'statusCode': 200,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'image_id': image_id,
                    'presigned_url': presigned_url,
                    'metadata': metadata
                })
            }
        else:
            # Step 4b: Return image data directly
            image_data = s3_client.get_image(metadata['s3_key'])
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': metadata.get('content_type', 'image/jpeg'),
                    'Content-Disposition': f'inline; filename="{metadata.get("filename", "image")}"'
                },
                'body': image_base64,
                'isBase64Encoded': True
            }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }

