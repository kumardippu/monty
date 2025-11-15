"""Lambda function: List all images with filters."""
import json
from typing import Dict, Any

from utils.dynamodb_client import DynamoDBClient

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """List all images with optional filters.
    
    What it does:
    1. Gets filter parameters from request
    2. Queries DynamoDB for images
    3. Applies filters (user_id, content_type)
    4. Returns list of images
    
    Expected request:
    {
        "queryStringParameters": {
            "user_id": "user123",        // Optional: filter by user
            "content_type": "image/jpeg", // Optional: filter by type
            "limit": "50"                 // Optional: max results
        }
    }
    """
    try:
        # Step 1: Get filter parameters
        query_params = event.get('queryStringParameters') or {}
        user_id = query_params.get('user_id')
        content_type = query_params.get('content_type')
        limit = int(query_params.get('limit', 100))
        
        # Step 2: Validate limit
        if limit < 1 or limit > 1000:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Limit must be between 1 and 1000'})
            }
        
        # Step 3: Get images from DynamoDB
        db_client = DynamoDBClient(table_name='image-metadata')
        images = db_client.list_images(
            user_id=user_id,
            content_type=content_type,
            limit=limit
        )
        
        # Step 4: Return results
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'count': len(images),
                'images': images
            })
        }
        
    except ValueError as e:
        return {
            'statusCode': 400,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'Invalid parameter: {str(e)}'})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }

