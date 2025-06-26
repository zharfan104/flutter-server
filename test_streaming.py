#!/usr/bin/env python3
"""
Test script for streaming AI code modification functionality
"""

import requests
import json
import time
import sys

def test_streaming_modification():
    """Test the streaming code modification endpoint"""
    print("Testing streaming code modification...")
    
    # API endpoint
    url = "http://localhost:5000/api/stream/modify-code"
    
    # Test request
    request_data = {
        "description": "Add a simple counter widget that increments when tapped",
        "user_id": "test_user"
    }
    
    print(f"Sending request: {json.dumps(request_data, indent=2)}")
    print("-" * 50)
    
    try:
        # Make streaming request
        response = requests.post(
            url,
            json=request_data,
            stream=True,
            headers={
                'Accept': 'text/event-stream',
                'Cache-Control': 'no-cache'
            }
        )
        
        if response.status_code != 200:
            print(f"Error: Server returned status {response.status_code}")
            print(response.text)
            return
        
        # Process streaming response
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                
                # Parse SSE format
                if line_str.startswith('event:'):
                    event_type = line_str[6:].strip()
                    print(f"\n[EVENT: {event_type}]")
                    
                elif line_str.startswith('data:'):
                    data_str = line_str[5:].strip()
                    if data_str:
                        try:
                            data = json.loads(data_str)
                            
                            # Handle different event types
                            if 'stage' in data:
                                progress = data.get('progress_percent', 0)
                                message = data.get('message', '')
                                print(f"[{progress:>3.0f}%] {message}")
                                
                                if data.get('metadata'):
                                    metadata = data['metadata']
                                    if 'current_file' in metadata:
                                        print(f"       File: {metadata['current_file']}")
                                    if 'text_chunk' in metadata and len(metadata['text_chunk']) > 0:
                                        # Show a snippet of the generated code
                                        chunk = metadata['text_chunk']
                                        if len(chunk) > 100:
                                            chunk = chunk[:100] + "..."
                                        print(f"       Code: {chunk}")
                                        
                            elif 'text' in data:
                                # Raw text chunk
                                sys.stdout.write(data['text'])
                                sys.stdout.flush()
                                
                            elif data.get('event_type') == 'result':
                                # Final result
                                print("\n" + "=" * 50)
                                print("FINAL RESULT:")
                                print(f"Modified files: {data.get('modified_files', [])}")
                                print(f"Created files: {data.get('created_files', [])}")
                                print(f"Success: {data.get('success', False)}")
                                
                        except json.JSONDecodeError as e:
                            print(f"Failed to parse JSON: {e}")
                            print(f"Raw data: {data_str}")
        
        print("\n" + "-" * 50)
        print("Streaming test completed!")
        
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"Unexpected error: {e}")

def test_basic_health_check():
    """Test if the server is running"""
    try:
        response = requests.get("http://localhost:5000/api/status")
        if response.status_code == 200:
            print("✓ Server is running")
            data = response.json()
            print(f"  Flutter status: {data.get('flutter_running', False)}")
            return True
        else:
            print("✗ Server returned error")
            return False
    except requests.exceptions.ConnectionError:
        print("✗ Cannot connect to server at http://localhost:5000")
        print("  Make sure the Flutter server is running: python run.py")
        return False

if __name__ == "__main__":
    print("Flutter Server Streaming Test")
    print("=" * 50)
    
    # Check if server is running
    if test_basic_health_check():
        print("\nStarting streaming test in 2 seconds...")
        time.sleep(2)
        test_streaming_modification()
    else:
        print("\nPlease start the server first!")