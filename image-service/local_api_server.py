"""Simple HTTP server to test Lambda functions locally.
This converts HTTP requests into Lambda events and calls the handlers."""
import json
import base64
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import sys
from pathlib import Path

# Add src to path so we can import handlers
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Set up LocalStack connection
os.environ['S3_ENDPOINT_URL'] = 'http://localhost:4566'
os.environ['DYNAMODB_ENDPOINT_URL'] = 'http://localhost:4566'
os.environ['AWS_ACCESS_KEY_ID'] = 'test'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'test'
os.environ['AWS_REGION'] = 'us-east-1'

# Import handlers
from handlers.upload_handler import lambda_handler as upload_handler
from handlers.list_handler import lambda_handler as list_handler
from handlers.view_handler import lambda_handler as view_handler
from handlers.delete_handler import lambda_handler as delete_handler


class APIHandler(BaseHTTPRequestHandler):
    """HTTP handler that converts requests to Lambda events."""
    
    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-User-Id')
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        query_params = parse_qs(parsed.query)
        
        # Convert query params from list to single values
        query_string_params = {k: v[0] if v else None for k, v in query_params.items()}
        
        # Route: GET /images -> list_handler
        if path == '/images' or path == '/images/':
            event = {
                'queryStringParameters': query_string_params,
                'headers': dict(self.headers)
            }
            response = list_handler(event, None)
            self._send_response(response)
        
        # Route: GET /images/{image_id} -> view_handler
        elif path.startswith('/images/') and len(path.split('/')) == 3:
            parts = path.split('/')
            image_id = parts[2]
            event = {
                'pathParameters': {'image_id': image_id},
                'queryStringParameters': query_string_params,
                'headers': dict(self.headers)
            }
            response = view_handler(event, None)
            self._send_response(response)
        
        else:
            self._send_error(404, 'Not Found')
    
    def do_POST(self):
        """Handle POST requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        query_params = parse_qs(parsed.query)
        query_string_params = {k: v[0] if v else None for k, v in query_params.items()}
        
        # Route: POST /images/upload -> upload_handler
        if path == '/images/upload' or path == '/images/upload/':
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            
            # Check if it's binary (image) or base64
            is_base64 = self.headers.get('Content-Type', '').startswith('image/')
            
            if is_base64:
                body_str = base64.b64encode(body).decode('utf-8')
            else:
                body_str = body.decode('utf-8')
            
            event = {
                'body': body_str,
                'isBase64Encoded': is_base64,
                'headers': dict(self.headers),
                'queryStringParameters': query_string_params
            }
            response = upload_handler(event, None)
            self._send_response(response)
        
        else:
            self._send_error(404, 'Not Found')
    
    def do_DELETE(self):
        """Handle DELETE requests."""
        parsed = urlparse(self.path)
        path = parsed.path
        
        # Route: DELETE /images/{image_id} -> delete_handler
        if path.startswith('/images/') and len(path.split('/')) == 3:
            parts = path.split('/')
            image_id = parts[2]
            event = {
                'pathParameters': {'image_id': image_id},
                'headers': dict(self.headers)
            }
            response = delete_handler(event, None)
            self._send_response(response)
        
        else:
            self._send_error(404, 'Not Found')
    
    def _send_response(self, lambda_response):
        """Send Lambda response as HTTP response."""
        status_code = lambda_response.get('statusCode', 200)
        headers = lambda_response.get('headers', {})
        body = lambda_response.get('body', '')
        is_base64 = lambda_response.get('isBase64Encoded', False)
        
        self.send_response(status_code)
        
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        
        # Add response headers
        for key, value in headers.items():
            self.send_header(key, value)
        
        self.end_headers()
        
        # Send body
        if is_base64:
            self.wfile.write(base64.b64decode(body))
        else:
            self.wfile.write(body.encode('utf-8'))
    
    def _send_error(self, status_code, message):
        """Send error response."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        error_body = json.dumps({'error': message})
        self.wfile.write(error_body.encode('utf-8'))
    
    def log_message(self, format, *args):
        """Override to show cleaner logs."""
        print(f"[{self.address_string()}] {format % args}")


def main():
    """Start the HTTP server."""
    port = 8000
    server = HTTPServer(('localhost', port), APIHandler)
    print(f"Local API Server running on http://localhost:{port}")
    print(f"Endpoints:")
    print(f"  - POST   /images/upload")
    print(f"  - GET    /images")
    print(f"  - GET    /images/{{image_id}}")
    print(f"  - DELETE /images/{{image_id}}")
    print(f"\nPress Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServer stopped")
        server.shutdown()


if __name__ == '__main__':
    main()

