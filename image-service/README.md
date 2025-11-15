# Instagram-like Image Upload Service

A scalable image upload and storage service using AWS Lambda, S3, and DynamoDB.

---

## Features

1. **Upload** images with metadata
2. **List** images with filters (user_id, content_type)
3. **View/Download** images
4. **Delete** images

---

## Architecture

```
Client → API Gateway → Lambda Functions → S3 (images) + DynamoDB (metadata)
```

**Components:**
- **API Gateway**: Routes HTTP requests to Lambda functions
- **Lambda Functions**: Serverless functions handling business logic
- **S3**: Object storage for images
- **DynamoDB**: NoSQL database for image metadata

---

## Project Structure

```
image-service/
├── src/
│   ├── handlers/              # Lambda function handlers
│   │   ├── upload_handler.py  # POST /images/upload
│   │   ├── list_handler.py    # GET /images
│   │   ├── view_handler.py    # GET /images/{id}
│   │   └── delete_handler.py  # DELETE /images/{id}
│   └── utils/                 # Helper modules
│       ├── s3_client.py       # S3 operations
│       └── dynamodb_client.py # DynamoDB operations
├── tests/
│   └── test_handlers.py       # Unit tests
├── local_api_server.py        # FastAPI server for local testing
├── setup_localstack.py        # LocalStack setup script
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

---

## Setup & Installation

### Prerequisites
- Docker (for LocalStack)
- Python 3.7+

### 1. Start LocalStack

```bash
cd /Users/dippukumar/Documents/projects/monty
docker-compose up -d
```

### 2. Install Dependencies

```bash
cd image-service
pip install -r requirements.txt
```

### 3. Setup LocalStack Resources

```bash
python setup_localstack.py
```

This creates:
- S3 bucket: `images`
- DynamoDB table: `image-metadata`

### 4. Start Local API Server

```bash
python local_api_server.py
```

Server will start on `http://localhost:8000`

**Interactive API Documentation:**
- **Swagger UI:** `http://localhost:8000/docs` - Interactive testing interface
- **ReDoc:** `http://localhost:8000/redoc` - Clean, readable documentation
- Test all endpoints directly from your browser

---

## API Documentation

**Note:** Interactive documentation available at:
- **Swagger UI:** `http://localhost:8000/docs` - Test endpoints with a UI
- **ReDoc:** `http://localhost:8000/redoc` - Read-only documentation

---

### 1. Upload Image

**Endpoint:** `POST /images/upload`

**Headers:**
- `X-User-Id`: User identifier (required)
- `Content-Type`: Image MIME type (e.g., `image/png`)

**Query Parameters:**
- `filename`: Image filename (optional)
- `metadata`: JSON metadata (optional)

**Example:**
```bash
curl --location 'http://localhost:8000/images/upload' \
  --header 'X-User-Id: user123' \
  --header 'Content-Type: image/png' \
  --data-binary '@photo.png'
```

**Response:**
```json
{
  "image_id": "abc-123-def",
  "user_id": "user123",
  "filename": "image.jpg",
  "s3_url": "s3://images/images/user123/abc-123-def/image.jpg",
  "size": 12345
}
```

---

### 2. List Images

**Endpoint:** `GET /images`

**Query Parameters:**
- `user_id`: Filter by user (optional)
- `content_type`: Filter by content type (optional)
- `limit`: Max results (default: 100, max: 1000)

**Examples:**
```bash
# List all images
curl http://localhost:8000/images

# Filter by user
curl 'http://localhost:8000/images?user_id=user123'

# Filter by content type
curl 'http://localhost:8000/images?content_type=image/png'

# Multiple filters
curl 'http://localhost:8000/images?user_id=user123&content_type=image/png&limit=10'
```

**Response:**
```json
{
  "count": 2,
  "images": [
    {
      "image_id": "abc-123",
      "user_id": "user123",
      "filename": "photo.png",
      "content_type": "image/png",
      "size": 12345,
      "created_at": "2024-01-01T00:00:00"
    }
  ]
}
```

---

### 3. View/Download Image

**Endpoint:** `GET /images/{image_id}`

**Query Parameters:**
- `download`: Set to `true` for presigned URL (optional)

**Examples:**
```bash
# Get image data
curl http://localhost:8000/images/abc-123-def

# Get download URL
curl 'http://localhost:8000/images/abc-123-def?download=true'
```

**Response (download=true):**
```json
{
  "image_id": "abc-123-def",
  "presigned_url": "http://localhost:4566/...",
  "metadata": {...}
}
```

---

### 4. Delete Image

**Endpoint:** `DELETE /images/{image_id}`

**Headers:**
- `X-User-Id`: User identifier (must own the image)

**Example:**
```bash
curl -X DELETE http://localhost:8000/images/abc-123-def \
  --header 'X-User-Id: user123'
```

**Response:**
```json
{
  "message": "Image deleted successfully",
  "image_id": "abc-123-def"
}
```

---

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

**Test Coverage:**
- Upload: Valid upload, missing user ID, empty file
- List: All images, filtered by user, filtered by content type
- View: Success, not found, with presigned URL
- Delete: Success, unauthorized, not found

---

## Database Schema

**DynamoDB Table: `image-metadata`**

| Attribute | Type | Description |
|-----------|------|-------------|
| image_id | String (PK) | Unique image identifier |
| user_id | String | User who uploaded the image |
| filename | String | Original filename |
| s3_key | String | S3 object key |
| content_type | String | MIME type (e.g., image/png) |
| size | Number | File size in bytes |
| metadata | String | JSON metadata (optional) |
| created_at | String | ISO 8601 timestamp |

---

## Technologies

- **Python 3.7+**: Programming language
- **AWS Lambda**: Serverless compute
- **AWS S3**: Object storage
- **AWS DynamoDB**: NoSQL database
- **AWS API Gateway**: REST API (simulated locally)
- **LocalStack**: Local AWS cloud stack
- **FastAPI**: Local development server with interactive docs
- **pytest**: Testing framework

---

## Scalability

This architecture is designed for high scalability:

1. **Lambda Functions**: Auto-scale based on request volume
2. **S3**: Unlimited storage capacity
3. **DynamoDB**: Auto-scaling with PAY_PER_REQUEST billing
4. **Stateless**: Each request is independent

---

## Security Considerations

**Implemented:**
- User authorization for delete operations

**Production Recommendations:**
- Add authentication (Cognito, JWT)
- Implement rate limiting
- Add file type validation
- Enable CloudWatch logging
- Use IAM roles with least privilege
- Enable S3 bucket encryption

---

## Troubleshooting

**"NoSuchBucket" error:**
```bash
python setup_localstack.py
```

**"Connection refused":**
```bash
# Check LocalStack
docker-compose up -d
```

**Port 8000 in use:**
```bash
lsof -ti:8000 | xargs kill -9
```

---
