"""Lambda function: Delete an image."""
import json
from typing import Dict, Any

from utils.s3_client import S3Client
from utils.dynamodb_client import DynamoDBClient

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Delete an image.
    
    What it does:
    1. Gets image ID from URL path
    2. Gets user ID from headers
    3. Checks if user owns the image (security!)
    4. Deletes image from S3
    5. Deletes metadata from DynamoDB
    
    Expected request:
    {
        "pathParameters": {
            "image_id": "uuid-here"
        },
        "headers": {
            "X-User-Id": "user123"  // Must match image owner
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
        
        # Step 2: Get user ID from headers
        headers = {k.lower(): v for k, v in event.get('headers', {}).items()}
        user_id = headers.get('x-user-id')
        
        if not user_id:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'X-User-Id header is required'})
            }
        
        # Step 3: Get image metadata
        db_client = DynamoDBClient(table_name='image-metadata')
        metadata = db_client.get_metadata(image_id)
        
        if not metadata:
            return {
                'statusCode': 404,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Image not found'})
            }
        
        # Step 4: Check if user owns this image (security check!)
        if metadata.get('user_id') != user_id:
            return {
                'statusCode': 403,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'You can only delete your own images'})
            }
        
        # Step 5: Delete from S3
        s3_client = S3Client(bucket_name='images')
        s3_client.delete_image(metadata['s3_key'])
        
        # Step 6: Delete from DynamoDB
        db_client.delete_metadata(image_id)
        
        # Step 7: Return success
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'message': 'Image deleted successfully',
                'image_id': image_id
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }

