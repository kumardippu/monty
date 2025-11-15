# 📚 Step-by-Step Tutorial: How Everything Works

Let me walk you through **exactly** what happens in this image service.

---

## 🎬 The Setup Phase (One Time)

### Step 1: Starting LocalStack

```bash
docker-compose up -d
```

**What happens:**
1. Docker starts a container running LocalStack
2. LocalStack creates fake AWS services on your computer
3. Services available: S3 (port 4566), DynamoDB (port 4566)
4. These act **exactly** like real AWS, but locally

**Why we need it:**
- Real AWS costs money
- LocalStack is free and works offline
- Perfect for development and testing

---

### Step 2: Running Setup Script

```bash
python setup_localstack.py
```

**What happens:**

1. **Script connects to LocalStack:**
   ```python
   s3 = boto3.client('s3', endpoint_url='http://localhost:4566')
   ```
   - `boto3` = Python library to talk to AWS
   - `endpoint_url` = Tell boto3 to use LocalStack instead of real AWS

2. **Creates S3 Bucket:**
   ```python
   s3.create_bucket(Bucket='images')
   ```
   - Bucket = Like a folder in the cloud
   - Named "images"
   - Will store all our photos

3. **Creates DynamoDB Table:**
   ```python
   dynamodb.create_table(
       TableName='image-metadata',
       KeySchema=[{'AttributeName': 'image_id', 'KeyType': 'HASH'}]
   )
   ```
   - Table = Like a spreadsheet
   - Each row = info about one image
   - Key = `image_id` (how we find each row)

**Result:** Now we have storage ready!

---

### Step 3: Starting Local Server

```bash
python local_api_server.py
```

**What happens:**

1. **Server starts listening:**
   ```python
   server = HTTPServer(('localhost', 8000), APIHandler)
   ```
   - Opens port 8000
   - Waits for HTTP requests

2. **Sets up environment:**
   ```python
   os.environ['S3_ENDPOINT_URL'] = 'http://localhost:4566'
   os.environ['DYNAMODB_ENDPOINT_URL'] = 'http://localhost:4566'
   ```
   - Tells all handlers to use LocalStack

3. **Imports Lambda handlers:**
   ```python
   from handlers.upload_handler import lambda_handler as upload_handler
   ```
   - Loads all 4 Lambda functions

**Result:** Server running on `http://localhost:8000` ready to receive requests!

---

## 📸 Upload Flow (Step-by-Step)

Let's upload an image:

```bash
curl --location 'http://localhost:8000/images/upload' \
  --header 'X-User-Id: alice' \
  --header 'Content-Type: image/png' \
  --data-binary '@photo.png'
```

### What Happens:

#### **Step 1: Request Arrives at Server** (`local_api_server.py`)

```python
def do_POST(self):
    parsed = urlparse(self.path)  # Parse URL
    path = parsed.path            # Get: "/images/upload"
```

**Decision made:** "This is POST to `/images/upload`, call `upload_handler`"

---

#### **Step 2: Server Reads the Image Data**

```python
content_length = int(self.headers.get('Content-Length', 0))
body = self.rfile.read(content_length)
```

**What this does:**
- Reads the entire photo file into memory
- `body` now contains the raw image bytes

---

#### **Step 3: Server Converts to Lambda Event**

```python
event = {
    'body': base64.b64encode(body).decode('utf-8'),  # Encode image
    'isBase64Encoded': True,
    'headers': dict(self.headers),  # {'X-User-Id': 'alice', ...}
    'queryStringParameters': query_string_params
}
```

**What this does:**
- Wraps everything in API Gateway format
- Base64 encodes the image (so it's text-safe)

---

#### **Step 4: Calls Upload Handler** (`upload_handler.py`)

```python
response = upload_handler(event, None)
```

Now we're inside the Lambda function!

---

#### **Step 5: Extract User Info**

```python
headers = {k.lower(): v for k, v in event.get('headers', {}).items()}
user_id = headers.get('x-user-id')  # Gets: "alice"
```

**Security check:**
```python
if not user_id:
    return {'statusCode': 400, 'body': 'User ID required'}
```

---

#### **Step 6: Decode the Image**

```python
if event.get('isBase64Encoded', False):
    image_data = base64.b64decode(body)  # Convert back to bytes
```

**Now we have:**
- `image_data` = Raw photo bytes (actual image file)

---

#### **Step 7: Generate Unique ID**

```python
image_id = str(uuid.uuid4())  # Example: "abc-123-def-456"
```

**Why UUID?**
- Universally Unique Identifier
- Guarantees no two images have same ID
- Works even if multiple users upload at same time

---

#### **Step 8: Create S3 Path**

```python
s3_key = f"images/{user_id}/{image_id}/{filename}"
# Example: "images/alice/abc-123-def-456/photo.png"
```

**Structure:**
```
images/
  └── alice/              ← User folder
      └── abc-123-def-456/ ← Image ID folder
          └── photo.png   ← Actual file
```

---

#### **Step 9: Upload to S3** (`s3_client.py`)

```python
s3_client = S3Client(bucket_name='images')
s3_url = s3_client.upload_image(
    image_data=image_data,
    key=s3_key,
    content_type='image/png'
)
```

**Inside S3Client:**

1. **Connect to S3:**
   ```python
   self.s3 = boto3.client('s3', endpoint_url='http://localhost:4566')
   ```

2. **Upload the file:**
   ```python
   self.s3.put_object(
       Bucket='images',
       Key='images/alice/abc-123-def-456/photo.png',
       Body=image_data,  # The actual photo bytes
       ContentType='image/png'
   )
   ```

3. **LocalStack receives this:**
   - Stores the file in memory (or disk)
   - Returns success

**Result:** Photo is now in S3! 🎉

---

#### **Step 10: Save Metadata to DynamoDB** (`dynamodb_client.py`)

```python
db_client = DynamoDBClient(table_name='image-metadata')
db_client.save_metadata(
    image_id='abc-123-def-456',
    user_id='alice',
    filename='photo.png',
    s3_key='images/alice/abc-123-def-456/photo.png',
    content_type='image/png',
    size=12345,
    metadata={}
)
```

**Inside DynamoDBClient:**

1. **Create the record:**
   ```python
   item = {
       'image_id': 'abc-123-def-456',
       'user_id': 'alice',
       'filename': 'photo.png',
       's3_key': 'images/alice/abc-123-def-456/photo.png',
       'content_type': 'image/png',
       'size': 12345,
       'created_at': '2024-01-01T10:00:00'
   }
   ```

2. **Save to DynamoDB:**
   ```python
   self.table.put_item(Item=item)
   ```

3. **LocalStack receives this:**
   - Adds row to the table
   - Returns success

**Result:** Photo info is now in DynamoDB! 📝

---

#### **Step 11: Return Success Response**

```python
return {
    'statusCode': 201,  # 201 = Created
    'body': json.dumps({
        'image_id': 'abc-123-def-456',
        'user_id': 'alice',
        'filename': 'photo.png',
        's3_url': 's3://images/images/alice/abc-123-def-456/photo.png',
        'size': 12345
    })
}
```

**Server sends this back to you!**

---

## 📋 List Flow (Step-by-Step)

```bash
curl 'http://localhost:8000/images?user_id=alice'
```

### What Happens:

#### **Step 1: Request Arrives**

```python
path = '/images'  # GET request
query_params = {'user_id': 'alice'}
```

#### **Step 2: Call List Handler**

```python
response = list_handler(event, None)
```

#### **Step 3: Extract Filters**

```python
user_id = query_params.get('user_id')  # 'alice'
content_type = query_params.get('content_type')  # None
limit = int(query_params.get('limit', 100))  # 100
```

#### **Step 4: Query DynamoDB**

```python
db_client = DynamoDBClient(table_name='image-metadata')
images = db_client.list_images(user_id='alice', limit=100)
```

**Inside DynamoDBClient:**

1. **Scan the table:**
   ```python
   response = self.table.scan(Limit=100)
   images = response['Items']  # All rows
   ```

2. **Apply filter:**
   ```python
   if user_id:
       images = [img for img in images if img.get('user_id') == 'alice']
   ```

**Result:** List of all Alice's photos

#### **Step 5: Return Results**

```python
return {
    'statusCode': 200,
    'body': json.dumps({
        'count': 2,
        'images': [
            {'image_id': 'abc-123', 'filename': 'photo1.png', ...},
            {'image_id': 'def-456', 'filename': 'photo2.png', ...}
        ]
    })
}
```

---

## 👁️ View Flow (Step-by-Step)

```bash
curl 'http://localhost:8000/images/abc-123-def-456'
```

### What Happens:

#### **Step 1: Extract Image ID**

```python
path_params = {'image_id': 'abc-123-def-456'}
image_id = path_params.get('image_id')
```

#### **Step 2: Get Metadata from DynamoDB**

```python
db_client = DynamoDBClient(table_name='image-metadata')
metadata = db_client.get_metadata('abc-123-def-456')
```

**What we get:**
```python
{
    'image_id': 'abc-123-def-456',
    'user_id': 'alice',
    's3_key': 'images/alice/abc-123-def-456/photo.png',
    'content_type': 'image/png'
}
```

#### **Step 3: Get Image from S3**

```python
s3_client = S3Client(bucket_name='images')
image_data = s3_client.get_image('images/alice/abc-123-def-456/photo.png')
```

**Inside S3Client:**
```python
response = self.s3.get_object(
    Bucket='images',
    Key='images/alice/abc-123-def-456/photo.png'
)
return response['Body'].read()  # Returns the photo bytes
```

#### **Step 4: Encode and Return**

```python
image_base64 = base64.b64encode(image_data).decode('utf-8')

return {
    'statusCode': 200,
    'headers': {'Content-Type': 'image/png'},
    'body': image_base64,
    'isBase64Encoded': True
}
```

**Browser receives this and displays the image!**

---

## 🗑️ Delete Flow (Step-by-Step)

```bash
curl -X DELETE 'http://localhost:8000/images/abc-123-def-456' \
  --header 'X-User-Id: alice'
```

### What Happens:

#### **Step 1: Security Check**

```python
user_id = headers.get('x-user-id')  # 'alice'
metadata = db_client.get_metadata('abc-123-def-456')

if metadata.get('user_id') != user_id:
    return {'statusCode': 403, 'body': 'Unauthorized'}
```

**This prevents:** Bob from deleting Alice's photos!

#### **Step 2: Delete from S3**

```python
s3_client = S3Client(bucket_name='images')
s3_client.delete_image('images/alice/abc-123-def-456/photo.png')
```

**Inside S3Client:**
```python
self.s3.delete_object(
    Bucket='images',
    Key='images/alice/abc-123-def-456/photo.png'
)
```

**Result:** Photo deleted from storage!

#### **Step 3: Delete from DynamoDB**

```python
db_client.delete_metadata('abc-123-def-456')
```

**Inside DynamoDBClient:**
```python
self.table.delete_item(Key={'image_id': 'abc-123-def-456'})
```

**Result:** Metadata deleted from database!

#### **Step 4: Confirm Deletion**

```python
return {
    'statusCode': 200,
    'body': json.dumps({
        'message': 'Image deleted successfully',
        'image_id': 'abc-123-def-456'
    })
}
```

---

## 🔄 Complete Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  YOU (curl command)                                             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ HTTP Request
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  local_api_server.py (Port 8000)                                │
│  - Receives HTTP request                                        │
│  - Parses URL and method                                        │
│  - Converts to Lambda event                                     │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            │ Lambda Event
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│  Lambda Handler (upload_handler.py, etc.)                       │
│  - Validates request                                            │
│  - Processes business logic                                     │
└──────────────┬────────────────────────────┬─────────────────────┘
               │                            │
               │                            │
               ↓                            ↓
┌──────────────────────────┐    ┌──────────────────────────┐
│  S3Client (s3_client.py) │    │  DynamoDBClient          │
│  - Uploads image         │    │  - Saves metadata        │
│  - Gets image            │    │  - Lists images          │
│  - Deletes image         │    │  - Gets metadata         │
└──────────────┬───────────┘    └──────────────┬───────────┘
               │                               │
               │ boto3                         │ boto3
               ↓                               ↓
┌──────────────────────────┐    ┌──────────────────────────┐
│  LocalStack S3           │    │  LocalStack DynamoDB     │
│  (Port 4566)             │    │  (Port 4566)             │
│                          │    │                          │
│  Bucket: images          │    │  Table: image-metadata   │
│  ├── alice/              │    │  ┌──────────────────┐   │
│  │   └── abc-123/       │    │  │ image_id (PK)    │   │
│  │       └── photo.png  │    │  │ user_id          │   │
│  └── bob/                │    │  │ filename         │   │
│      └── def-456/        │    │  │ s3_key           │   │
│          └── image.jpg   │    │  │ created_at       │   │
│                          │    │  └──────────────────┘   │
└──────────────────────────┘    └──────────────────────────┘
```

---

## 🎯 Key Concepts Explained

### 1. **Why Base64 Encoding?**

```python
body_str = base64.b64encode(body).decode('utf-8')
```

**Problem:** HTTP is text-based, images are binary
**Solution:** Convert binary to text using Base64

**Example:**
- Binary: `\x89PNG\r\n\x1a\n...` (can't send in JSON)
- Base64: `iVBORw0KGgoAAAANSUhEUgAA...` (text, safe for JSON)

---

### 2. **Why UUID for Image ID?**

```python
image_id = str(uuid.uuid4())  # "abc-123-def-456"
```

**Benefits:**
- Unique across entire system
- No need to check database for duplicates
- Can be generated offline
- Works with multiple servers

---

### 3. **Why Separate S3 and DynamoDB?**

**S3:** Stores large binary data (images)
- Optimized for big files
- Cheap storage
- Slow to search

**DynamoDB:** Stores small text data (metadata)
- Optimized for fast queries
- Can filter and search
- Fast but more expensive

**Together:** Best of both worlds!

---

### 4. **How Filters Work**

```python
# Filter in Python (after getting data)
images = [img for img in images if img.get('user_id') == 'alice']
```

**Process:**
1. Get ALL images from DynamoDB
2. Filter in Python code
3. Return only matching images

**Note:** In production, use DynamoDB indexes for faster filtering!

---

## 🧪 Try It Yourself

### Experiment 1: See the Data

```bash
# Upload an image
curl -X POST http://localhost:8000/images/upload \
  -H "X-User-Id: test" \
  -H "Content-Type: image/png" \
  --data-binary '@photo.png'

# Check S3
aws --endpoint-url http://localhost:4566 s3 ls s3://images/images/ --recursive

# Check DynamoDB
aws --endpoint-url http://localhost:4566 dynamodb scan \
  --table-name image-metadata
```

### Experiment 2: Add Debug Prints

In `upload_handler.py`:
```python
print(f"Received image from user: {user_id}")
print(f"Image size: {len(image_data)} bytes")
print(f"Saving to S3 key: {s3_key}")
```

Restart server and watch the logs!

---

## 📚 Summary

**Upload:** Client → Server → Lambda → S3 + DynamoDB → Response
**List:** Client → Server → Lambda → DynamoDB (filter) → Response
**View:** Client → Server → Lambda → DynamoDB (get key) → S3 (get file) → Response
**Delete:** Client → Server → Lambda → Check ownership → S3 (delete) + DynamoDB (delete) → Response

**That's it!** Every request follows this pattern. 🎉

