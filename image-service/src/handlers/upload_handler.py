"""Lambda function: Upload image with metadata."""
import json
import base64
import uuid
from typing import Dict, Any

from utils.s3_client import S3Client
from utils.dynamodb_client import DynamoDBClient


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Upload an image with metadata.
    
    Args:
        event: API Gateway event with image data
        context: Lambda context
        
    Returns:
        API Gateway response with image details
    """
    try:
        # Extract request data
        headers = {k.lower(): v for k, v in event.get('headers', {}).items()}
        query_params = event.get('queryStringParameters') or {}
        body = event.get('body', '')
        
        # Validate user ID
        user_id = headers.get('x-user-id')
        if not user_id:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'X-User-Id header is required'})
            }
        
        # Get filename and metadata
        filename = query_params.get('filename', 'image.jpg')
        metadata_str = query_params.get('metadata', '{}')
        try:
            metadata = json.loads(metadata_str) if metadata_str else {}
        except:
            metadata = {}
        
        # Decode image data
        if event.get('isBase64Encoded', False):
            image_data = base64.b64decode(body)
        else:
            image_data = body if isinstance(body, bytes) else body.encode()
        
        if len(image_data) == 0:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({'error': 'Image data is empty'})
            }
        
        # Generate unique image ID
        image_id = str(uuid.uuid4())
        content_type = headers.get('content-type', 'image/jpeg')
        s3_key = f"images/{user_id}/{image_id}/{filename}"
        
        # Upload to S3
        s3_client = S3Client(bucket_name='images')
        s3_url = s3_client.upload_image(
            image_data=image_data,
            key=s3_key,
            content_type=content_type
        )
        
        # Save metadata to DynamoDB
        db_client = DynamoDBClient(table_name='image-metadata')
        db_client.save_metadata(
            image_id=image_id,
            user_id=user_id,
            filename=filename,
            s3_key=s3_key,
            content_type=content_type,
            size=len(image_data),
            metadata=metadata
        )
        
        # Return success response
        return {
            'statusCode': 201,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'image_id': image_id,
                'user_id': user_id,
                'filename': filename,
                's3_url': s3_url,
                'content_type': content_type,
                'size': len(image_data),
                'metadata': metadata
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'error': f'Internal server error: {str(e)}'})
        }
