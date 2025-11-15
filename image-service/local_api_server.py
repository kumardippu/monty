"""FastAPI server to test Lambda functions locally.
This converts HTTP requests into Lambda events and calls the handlers."""
import os
import sys
from pathlib import Path

# Set up LocalStack connection before importing handlers
os.environ['S3_ENDPOINT_URL'] = 'http://localhost:4566'
os.environ['DYNAMODB_ENDPOINT_URL'] = 'http://localhost:4566'
os.environ['AWS_ACCESS_KEY_ID'] = 'test'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
os.environ['AWS_REGION'] = 'us-east-1'

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import json
import base64
from fastapi import FastAPI, Request, Header, Query
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from handlers.upload_handler import lambda_handler as upload_handler
from handlers.list_handler import lambda_handler as list_handler
from handlers.view_handler import lambda_handler as view_handler
from handlers.delete_handler import lambda_handler as delete_handler

app = FastAPI(title="Image Service API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/images/upload")
async def upload_image(
    request: Request,
    x_user_id: Optional[str] = Header(None),
    filename: Optional[str] = Query(None),
    metadata: Optional[str] = Query(None)
):
    """Upload an image with metadata."""
    body = await request.body()
    content_type = request.headers.get('content-type', 'image/jpeg')
    
    # Convert binary to base64 if it's an image
    is_base64 = content_type.startswith('image/')
    if is_base64:
        body_str = base64.b64encode(body).decode('utf-8')
    else:
        body_str = body.decode('utf-8')
    
    # Build query params
    query_params = {}
    if filename:
        query_params['filename'] = filename
    if metadata:
        query_params['metadata'] = metadata
    
    # Create Lambda event
    event = {
        'body': body_str,
        'isBase64Encoded': is_base64,
        'headers': dict(request.headers),
        'queryStringParameters': query_params if query_params else None
    }
    
    # Call Lambda handler
    lambda_response = upload_handler(event, None)
    return _process_lambda_response(lambda_response)


@app.get("/images")
async def list_images(
    request: Request,
    user_id: Optional[str] = Query(None),
    content_type: Optional[str] = Query(None),
    limit: Optional[int] = Query(None)
):
    """List all images with optional filters."""
    # Build query params
    query_params = {}
    if user_id:
        query_params['user_id'] = user_id
    if content_type:
        query_params['content_type'] = content_type
    if limit:
        query_params['limit'] = str(limit)
    
    # Create Lambda event
    event = {
        'queryStringParameters': query_params if query_params else None,
        'headers': dict(request.headers)
    }
    
    # Call Lambda handler
    lambda_response = list_handler(event, None)
    return _process_lambda_response(lambda_response)


@app.get("/images/{image_id}")
async def view_image(
    image_id: str,
    request: Request,
    download: Optional[bool] = Query(False)
):
    """View or download an image."""
    # Build query params
    query_params = {}
    if download:
        query_params['download'] = 'true'
    
    # Create Lambda event
    event = {
        'pathParameters': {'image_id': image_id},
        'queryStringParameters': query_params if query_params else None,
        'headers': dict(request.headers)
    }
    
    # Call Lambda handler
    lambda_response = view_handler(event, None)
    return _process_lambda_response(lambda_response)


@app.delete("/images/{image_id}")
async def delete_image(
    image_id: str,
    request: Request,
    x_user_id: Optional[str] = Header(None)
):
    """Delete an image."""
    # Create Lambda event
    event = {
        'pathParameters': {'image_id': image_id},
        'headers': dict(request.headers)
    }
    
    # Call Lambda handler
    lambda_response = delete_handler(event, None)
    return _process_lambda_response(lambda_response)


def _process_lambda_response(lambda_response: dict):
    """Convert Lambda response to FastAPI response."""
    status_code = lambda_response.get('statusCode', 200)
    headers = lambda_response.get('headers', {})
    body = lambda_response.get('body', '')
    is_base64 = lambda_response.get('isBase64Encoded', False)
    
    # Decode base64 body if needed
    if is_base64:
        content = base64.b64decode(body)
        return Response(content=content, status_code=status_code, headers=headers)
    else:
        # Parse JSON body
        try:
            body_json = json.loads(body) if body else {}
            return JSONResponse(content=body_json, status_code=status_code, headers=headers)
        except json.JSONDecodeError:
            return Response(content=body, status_code=status_code, headers=headers)


if __name__ == '__main__':
    import uvicorn
    print("Local API Server running on http://localhost:8000")
    print("\nEndpoints:")
    print("  - POST   /images/upload")
    print("  - GET    /images")
    print("  - GET    /images/{image_id}")
    print("  - DELETE /images/{image_id}")
    print("\nInteractive Documentation:")
    print("  - Swagger UI: http://localhost:8000/docs")
    print("  - ReDoc:      http://localhost:8000/redoc")
    print("\nPress Ctrl+C to stop")
    uvicorn.run(app, host="localhost", port=8000)

