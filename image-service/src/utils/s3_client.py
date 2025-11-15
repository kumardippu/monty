"""Simple S3 client for storing images."""
import boto3
import os

class S3Client:
    """Handles S3 operations for images."""
    
    def __init__(self, bucket_name: str):
        """Initialize S3 client.
        
        Args:
            bucket_name: Name of the S3 bucket (e.g., 'images')
        """
        self.bucket_name = bucket_name
        # Connect to LocalStack or real AWS
        endpoint = os.getenv('S3_ENDPOINT_URL', 'http://localhost:4566')
        self.s3 = boto3.client(
            's3',
            endpoint_url=endpoint,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID', 'test'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY', 'test'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        # Auto-create bucket if it doesn't exist (for LocalStack)
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Create bucket if it doesn't exist (only for LocalStack)."""
        endpoint = os.getenv('S3_ENDPOINT_URL', '')
        # Only auto-create for LocalStack
        if 'localhost' not in endpoint and '127.0.0.1' not in endpoint:
            return
        
        # For LocalStack, just try to create (ignore if already exists)
        try:
            self.s3.create_bucket(Bucket=self.bucket_name)
        except Exception as e:
            # Ignore "already exists" errors - that's fine
            if 'BucketAlreadyExists' not in str(e) and 'BucketAlreadyOwnedByYou' not in str(e):
                # Some other error - but don't fail here, let upload handle it
                pass
    
    def upload_image(self, image_data: bytes, key: str, content_type: str) -> str:
        """Upload image to S3.
        
        Args:
            image_data: The image file data (bytes)
            key: S3 object key (path where image will be stored)
            content_type: Image type (e.g., 'image/jpeg')
            
        Returns:
            S3 URL of the uploaded image
        """
        try:
            self.s3.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=image_data,
                ContentType=content_type
            )
            return f"s3://{self.bucket_name}/{key}"
        except Exception as e:
            # If bucket doesn't exist, create it and retry (for LocalStack only)
            error_str = str(e)
            if 'NoSuchBucket' in error_str or 'does not exist' in error_str.lower():
                endpoint = os.getenv('S3_ENDPOINT_URL', '')
                if 'localhost' in endpoint or '127.0.0.1' in endpoint:
                    # Try to create bucket
                    try:
                        self.s3.create_bucket(Bucket=self.bucket_name)
                    except Exception as create_error:
                        # Ignore "already exists" - bucket might be there now
                        if 'BucketAlreadyExists' not in str(create_error) and 'BucketAlreadyOwnedByYou' not in str(create_error):
                            # Real error - re-raise original
                            raise e
                    
                    # Retry upload
                    self.s3.put_object(
                        Bucket=self.bucket_name,
                        Key=key,
                        Body=image_data,
                        ContentType=content_type
                    )
                    return f"s3://{self.bucket_name}/{key}"
            # Not a bucket error, re-raise
            raise
    
    def get_image(self, key: str) -> bytes:
        """Download image from S3.
        
        Args:
            key: S3 object key (path to the image)
            
        Returns:
            Image data as bytes
        """
        response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
        return response['Body'].read()
    
    def delete_image(self, key: str):
        """Delete image from S3.
        
        Args:
            key: S3 object key (path to the image)
        """
        self.s3.delete_object(Bucket=self.bucket_name, Key=key)
    
    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        """Generate a presigned URL for temporary access.
        
        Args:
            key: S3 object key
            expires_in: URL expiration time in seconds (default: 1 hour)
            
        Returns:
            Presigned URL string
        """
        url = self.s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': self.bucket_name, 'Key': key},
            ExpiresIn=expires_in
        )
        # Fix for LocalStack
        if 'localhost:4566' in os.getenv('S3_ENDPOINT_URL', ''):
            url = url.replace('https://', 'http://').replace(':443', ':4566')
        return url

