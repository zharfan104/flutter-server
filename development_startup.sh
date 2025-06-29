#!/bin/bash

# Flutter-Flask Development Startup Script
# This script cleanly kills all previous processes and starts the development server

set -e

echo "🚀 Flutter-Flask Development Startup"
echo "====================================="

# Function to print colored output
print_status() {
    echo -e "\033[1;32m[INFO]\033[0m $1"
}

print_warning() {
    echo -e "\033[1;33m[WARN]\033[0m $1"
}

print_error() {
    echo -e "\033[1;31m[ERROR]\033[0m $1"
}

# Function to kill processes safely
kill_processes() {
    print_status "Cleaning up previous processes..."
    
    # Kill Python processes related to our server
    print_status "Killing Python Flask processes..."
    pkill -f "python.*run.py" 2>/dev/null || true
    pkill -f "python.*flutter_server" 2>/dev/null || true
    pkill -f "flask.*run" 2>/dev/null || true
    
    # Kill Flutter processes (commented out for simplicity)
    # print_status "Killing Flutter processes..."
    # pkill -f "flutter run" 2>/dev/null || true
    # pkill -f "flutter.*web-server" 2>/dev/null || true
    # pkill -f "dart:flut" 2>/dev/null || true
    # pkill -9 -f "dart" 2>/dev/null || true
    
    # Kill processes on specific ports
    print_status "Freeing up ports 5000 and 8080..."
    
    # Kill processes on port 5000 (Flask)
    if lsof -Pi :5000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port 5000 is in use, killing processes..."
        lsof -Pi :5000 -sTCP:LISTEN -t | xargs kill -9 2>/dev/null || true
    fi
    
    # Check port 8080 (Flutter) but don't automatically kill
    if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port 8080 is in use (this is normal if Flutter is running)"
        # lsof -Pi :8080 -sTCP:LISTEN -t | xargs kill -9 2>/dev/null || true
    fi
    
    # Give processes time to cleanup
    sleep 2
    
    # Note: Port 8080 checking disabled for simplicity
    # if lsof -Pi :8080 -sTCP:LISTEN -t >/dev/null 2>&1; then
    #     print_warning "Port 8080 still in use, forcing cleanup..."
    #     lsof -Pi :8080 -sTCP:LISTEN -t | xargs kill -9 2>/dev/null || true
    #     sleep 1
    # fi
    
    print_status "Process cleanup complete!"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check if Poetry is installed
    if ! command -v poetry &> /dev/null; then
        print_error "Poetry is not installed. Please install Poetry first."
        exit 1
    fi
    
    # Check if Flutter is installed
    if ! command -v flutter &> /dev/null; then
        print_error "Flutter is not installed. Please install Flutter first."
        exit 1
    fi
    
    # Check if we're in the right directory
    if [[ ! -f "run.py" ]] || [[ ! -d "src" ]]; then
        print_error "Please run this script from the flutter-server directory."
        exit 1
    fi
    
    # Check if poetry.lock exists
    if [[ ! -f "poetry.lock" ]]; then
        print_warning "poetry.lock not found. Installing dependencies..."
        poetry install --no-root
    fi
    
    print_status "Prerequisites check complete!"
}

# Function to start the development server
start_server() {
    print_status "Starting Flutter-Flask development server..."
    
    # Ensure Poetry environment is set up
    print_status "Setting up Poetry environment..."
    poetry install --no-dev --no-root 2>/dev/null || poetry install --no-root
    
    print_status "Starting server with Poetry..."
    print_status "Server will be available at: http://localhost:5000"
    print_status "Press Ctrl+C to stop the server"
    echo ""
    
    # Start the server
    poetry run python run.py
}

# Function to handle cleanup on exit
cleanup_on_exit() {
    print_warning "Received interrupt signal. Cleaning up..."
    kill_processes
    print_status "Cleanup complete. Goodbye!"
    exit 0
}

# Trap Ctrl+C and call cleanup function
trap cleanup_on_exit SIGINT SIGTERM

# Main execution
main() {
    # Change to script directory
    cd "$(dirname "$0")"
    
    # Kill previous processes
    kill_processes
    
    # Check prerequisites
    check_prerequisites
    
    # Start the server
    start_server
}

# Run main function
main "$@"