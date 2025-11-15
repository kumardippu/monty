"""Unit tests for all Lambda handlers - Simple and easy to understand."""
import json
import base64
import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add src to path so we can import handlers
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from handlers.upload_handler import lambda_handler as upload_handler
from handlers.list_handler import lambda_handler as list_handler
from handlers.view_handler import lambda_handler as view_handler
from handlers.delete_handler import lambda_handler as delete_handler

# Sample image data (tiny valid JPEG)
SAMPLE_IMAGE = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xd9'


class TestUploadHandler:
    """Tests for upload handler."""
    
    @patch('handlers.upload_handler.S3Client')
    @patch('handlers.upload_handler.DynamoDBClient')
    def test_upload_success(self, mock_db, mock_s3):
        """Test: Upload image successfully."""
        # Setup mocks (fake S3 and DynamoDB)
        mock_s3_instance = Mock()
        mock_s3_instance.upload_image.return_value = 's3://images/user123/uuid/test.jpg'
        mock_s3.return_value = mock_s3_instance
        
        mock_db_instance = Mock()
        mock_db_instance.save_metadata.return_value = {'image_id': 'test-uuid'}
        mock_db.return_value = mock_db_instance
        
        # Create request
        event = {
            'body': base64.b64encode(SAMPLE_IMAGE).decode('utf-8'),
            'isBase64Encoded': True,
            'headers': {
                'Content-Type': 'image/jpeg',
                'X-User-Id': 'user123'
            },
            'queryStringParameters': {
                'filename': 'test.jpg',
                'metadata': '{"description": "Test"}'
            }
        }
        
        # Call handler
        response = upload_handler(event, None)
        
        # Check result
        assert response['statusCode'] == 201
        body = json.loads(response['body'])
        assert 'image_id' in body
        assert body['user_id'] == 'user123'
    
    def test_upload_missing_user_id(self):
        """Test: Upload without user ID should fail."""
        event = {
            'body': base64.b64encode(SAMPLE_IMAGE).decode('utf-8'),
            'isBase64Encoded': True,
            'headers': {}  # No X-User-Id
        }
        
        response = upload_handler(event, None)
        
        assert response['statusCode'] == 400
        body = json.loads(response['body'])
        assert 'X-User-Id' in body['error']


class TestListHandler:
    """Tests for list handler."""
    
    @patch('handlers.list_handler.DynamoDBClient')
    def test_list_all_images(self, mock_db):
        """Test: List all images."""
        mock_instance = Mock()
        mock_instance.list_images.return_value = [
            {'image_id': '1', 'filename': 'img1.jpg'},
            {'image_id': '2', 'filename': 'img2.jpg'}
        ]
        mock_db.return_value = mock_instance
        
        event = {'queryStringParameters': None}
        response = list_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert body['count'] == 2
    
    @patch('handlers.list_handler.DynamoDBClient')
    def test_list_with_filters(self, mock_db):
        """Test: List with user_id and content_type filters."""
        mock_instance = Mock()
        mock_instance.list_images.return_value = []
        mock_db.return_value = mock_instance
        
        event = {
            'queryStringParameters': {
                'user_id': 'user123',
                'content_type': 'image/jpeg',
                'limit': '10'
            }
        }
        
        response = list_handler(event, None)
        
        assert response['statusCode'] == 200
        # Check that filters were passed correctly
        mock_instance.list_images.assert_called_once_with(
            user_id='user123',
            content_type='image/jpeg',
            limit=10
        )


class TestViewHandler:
    """Tests for view handler."""
    
    @patch('handlers.view_handler.S3Client')
    @patch('handlers.view_handler.DynamoDBClient')
    def test_view_image(self, mock_db, mock_s3):
        """Test: View image directly."""
        mock_db_instance = Mock()
        mock_db_instance.get_metadata.return_value = {
            'image_id': 'test-uuid',
            's3_key': 'images/user123/test-uuid/image.jpg',
            'content_type': 'image/jpeg'
        }
        mock_db.return_value = mock_db_instance
        
        mock_s3_instance = Mock()
        mock_s3_instance.get_image.return_value = SAMPLE_IMAGE
        mock_s3.return_value = mock_s3_instance
        
        event = {
            'pathParameters': {'image_id': 'test-uuid'},
            'queryStringParameters': {}
        }
        
        response = view_handler(event, None)
        
        assert response['statusCode'] == 200
        assert response['isBase64Encoded'] == True
    
    @patch('handlers.view_handler.S3Client')
    @patch('handlers.view_handler.DynamoDBClient')
    def test_view_presigned_url(self, mock_db, mock_s3):
        """Test: Get presigned URL for download."""
        mock_db_instance = Mock()
        mock_db_instance.get_metadata.return_value = {
            'image_id': 'test-uuid',
            's3_key': 'images/user123/test-uuid/image.jpg'
        }
        mock_db.return_value = mock_db_instance
        
        mock_s3_instance = Mock()
        mock_s3_instance.get_presigned_url.return_value = 'https://presigned-url.com'
        mock_s3.return_value = mock_s3_instance
        
        event = {
            'pathParameters': {'image_id': 'test-uuid'},
            'queryStringParameters': {'download': 'true'}
        }
        
        response = view_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'presigned_url' in body


class TestDeleteHandler:
    """Tests for delete handler."""
    
    @patch('handlers.delete_handler.S3Client')
    @patch('handlers.delete_handler.DynamoDBClient')
    def test_delete_success(self, mock_db, mock_s3):
        """Test: Delete image successfully."""
        mock_db_instance = Mock()
        mock_db_instance.get_metadata.return_value = {
            'image_id': 'test-uuid',
            'user_id': 'user123',
            's3_key': 'images/user123/test-uuid/image.jpg'
        }
        mock_db.return_value = mock_db_instance
        
        mock_s3_instance = Mock()
        mock_s3.return_value = mock_s3_instance
        
        event = {
            'pathParameters': {'image_id': 'test-uuid'},
            'headers': {'X-User-Id': 'user123'}
        }
        
        response = delete_handler(event, None)
        
        assert response['statusCode'] == 200
        body = json.loads(response['body'])
        assert 'message' in body
    
    @patch('handlers.delete_handler.DynamoDBClient')
    def test_delete_unauthorized(self, mock_db):
        """Test: Cannot delete someone else's image."""
        mock_instance = Mock()
        mock_instance.get_metadata.return_value = {
            'image_id': 'test-uuid',
            'user_id': 'user456',  # Different user!
            's3_key': 'images/user456/test-uuid/image.jpg'
        }
        mock_db.return_value = mock_instance
        
        event = {
            'pathParameters': {'image_id': 'test-uuid'},
            'headers': {'X-User-Id': 'user123'}  # Trying to delete user456's image
        }
        
        response = delete_handler(event, None)
        
        assert response['statusCode'] == 403
        body = json.loads(response['body'])
        assert 'own images' in body['error']

