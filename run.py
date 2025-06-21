#!/usr/bin/env python3
"""
Flutter Server Runner
Run this script to start the Flutter development server with Poetry.
"""

import os
import sys
import subprocess

def check_flutter():
    """Check if Flutter is installed and available."""
    try:
        result = subprocess.run(['flutter', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ Flutter is installed")
            return True
        else:
            print("✗ Flutter check failed")
            return False
    except FileNotFoundError:
        print("✗ Flutter is not installed or not in PATH")
        return False

def check_poetry():
    """Check if we're running in Poetry environment."""
    # Check for Poetry environment variables or if running via poetry run
    if (os.environ.get('POETRY_ACTIVE') or 
        os.environ.get('VIRTUAL_ENV') and 'poetry' in os.environ.get('VIRTUAL_ENV', '') or
        'poetry' in sys.argv[0] or
        os.path.exists('poetry.lock')):
        print("✓ Running with Poetry")
        return True
    else:
        print("✗ Not running in Poetry environment")
        print("Please run: poetry run python run.py")
        return False

def main():
    print("Flutter Development Server")
    print("=" * 30)
    
    # Check requirements
    if not check_flutter():
        print("\nPlease install Flutter first:")
        print("https://docs.flutter.dev/get-started/install")
        sys.exit(1)
    
    if not check_poetry():
        print("\nTo run with Poetry:")
        print("poetry run python run.py")
        sys.exit(1)
    
    print("\n🚀 Starting Flutter development server...")
    print("Access the web interface at: http://localhost:5000")
    print("Press Ctrl+C to stop")
    
    # Import and run the main application
    from flutter_server import main as run_server
    try:
        run_server()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down Flutter development server...")
        sys.exit(0)

if __name__ == '__main__':
    main()