"""
Static Files Router

API endpoints for static file proxying to Flutter development server
"""

from flask import Blueprint, request, Response
import requests
from typing import List

# Create blueprint for static files routes
static_files_bp = Blueprint('static_files', __name__)

# Static file extensions to handle
STATIC_EXTENSIONS = [
    '.js', '.js.map', '.css', '.png', '.jpg', '.jpeg', '.gif', '.svg', 
    '.woff', '.woff2', '.ttf', '.ico', '.otf'
]

# Flutter specific routes
FLUTTER_ROUTES = [
    '/canvaskit/<path:path>',
    '/assets/<path:path>',
    '/manifest.json',
    '/favicon.ico',
    '/favicon.png',
    '/icons/<path:path>',
    '/flutter_bootstrap.js'
]


@static_files_bp.route('/canvaskit/<path:path>')
@static_files_bp.route('/assets/<path:path>')
@static_files_bp.route('/manifest.json')
@static_files_bp.route('/favicon.ico')
@static_files_bp.route('/favicon.png') 
@static_files_bp.route('/icons/<path:path>')
@static_files_bp.route('/flutter_bootstrap.js')
def flutter_static_assets(filename=None, path=None):
    """Proxy Flutter static assets to the Flutter development server"""
    try:
        # Build the correct URL based on the request
        request_path = request.path.lstrip('/')
        flutter_url = f'http://127.0.0.1:8080/{request_path}'
        
        resp = requests.get(flutter_url, stream=True, timeout=10)
        
        def generate():
            for chunk in resp.iter_content(chunk_size=1024):
                yield chunk
                
        # Set proper headers for static assets
        headers = {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
        
        # Copy important headers from Flutter server
        for header in ['Content-Type', 'Content-Length']:
            if header in resp.headers:
                headers[header] = resp.headers[header]
        
        return Response(generate(), 
                       status=resp.status_code,
                       headers=headers)
    except Exception as e:
        print(f"Error serving static asset {request.path}: {str(e)}")
        return f"Asset not available: {str(e)}", 404


@static_files_bp.route('/<path:filename>')
def static_file_handler(filename):
    """Handle static files like .js, .css, .png, etc."""
    
    # Check if this looks like a static asset based on extension
    if any(filename.endswith(ext) for ext in STATIC_EXTENSIONS):
        try:
            flutter_url = f'http://127.0.0.1:8080/{filename}'
            resp = requests.get(flutter_url, stream=True, timeout=10)
            
            def generate():
                for chunk in resp.iter_content(chunk_size=1024):
                    yield chunk
                    
            # Set proper headers for static assets
            headers = {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
            
            # Copy important headers from Flutter server
            for header in ['Content-Type', 'Content-Length']:
                if header in resp.headers:
                    headers[header] = resp.headers[header]
            
            return Response(generate(), 
                           status=resp.status_code,
                           headers=headers)
        except Exception as e:
            print(f"Error serving static file {filename}: {str(e)}")
            return f"Asset not available: {str(e)}", 404
    
    # Not a static asset, return 404
    return "Not Found", 404


@static_files_bp.route('/app')
@static_files_bp.route('/app/')
@static_files_bp.route('/app/<path:path>')
def flutter_app(path=''):
    """Proxy Flutter app requests to the Flutter development server with caching optimization"""
    try:
        flutter_url = f'http://127.0.0.1:8080/{path}'
        resp = requests.get(flutter_url, stream=True)
        
        def generate():
            for chunk in resp.iter_content(chunk_size=1024):
                yield chunk
        
        # Optimize headers for better performance
        headers = dict(resp.headers)
        
        # Add caching for static assets
        if any(ext in path for ext in ['.js', '.css', '.woff', '.woff2', '.ttf', '.otf']):
            headers['Cache-Control'] = 'public, max-age=3600, immutable'  # 1 hour cache
        elif any(ext in path for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico']):
            headers['Cache-Control'] = 'public, max-age=86400'  # 24 hour cache for images
        else:
            headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # No cache for HTML/main app
            
        # Enable compression hint
        if 'content-encoding' not in headers:
            headers['Vary'] = 'Accept-Encoding'
                
        return Response(generate(), 
                       status=resp.status_code,
                       headers=headers)
    except Exception as e:
        return f"Flutter app not available: {str(e)}", 503