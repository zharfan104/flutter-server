# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture

This is a containerized Flutter development environment that combines multiple services into a single Docker container:

- **Flask API Server** (`flutter_server.py`) manages Flutter processes and provides REST API
- **Flutter Development Server** runs on port 8080, managed as subprocess by Flask
- **Nginx Reverse Proxy** routes traffic: `/api/*` → Flask, `/app` → Flutter, `/` → Web Editor
- **Supervisor** manages all services in the container

The core component is the `FlutterManager` class which handles process lifecycle, hot reload, file operations, and git integration.

## Build and Development Commands

### Local Development with Poetry
```bash
# Install dependencies
poetry install

# Activate Poetry environment
poetry shell

# Run the development server
python run.py

# Or run directly with Poetry
poetry run python run.py

# Run with existing Flutter repository
REPO_URL=https://github.com/user/repo.git python run.py

# Run with private repository
REPO_URL=https://github.com/user/repo.git GITHUB_TOKEN=token python run.py
```

### Legacy Docker Development
```bash
# Build Docker image
docker build -t flutter-server .

# Run basic container (creates new Flutter project)
docker run -p 80:80 flutter-server
```

### Cloud Deployment
```bash
# Deploy to Google Cloud Build
python build.py
```

### API Testing
```bash
# Check Flutter status
curl http://localhost:5000/api/status

# Start Flutter development server
curl -X POST http://localhost:5000/api/start

# Update file with hot reload
curl -X PUT http://localhost:5000/api/file/lib/main.dart \
  -H "Content-Type: application/json" \
  -d '{"content": "dart_code", "auto_reload": true}'

# Trigger hot reload manually
curl -X POST http://localhost:5000/api/hot-reload

# Pull git changes and hot reload
curl -X POST http://localhost:5000/api/git-pull
```

## Key Implementation Details

### Flutter Process Management
- Flutter runs via `subprocess.Popen` with stdin/stdout pipes for hot reload commands
- Output is continuously buffered (max 1000 lines, truncated to 500)
- Hot reload triggered by sending 'r\n' to process stdin
- Process health monitored via `poll()` method

### File System Operations
- Project files stored in `./project/` relative to current working directory
- File updates automatically trigger hot reload for `.dart` files
- Supports both individual file updates and batch operations

### Git Integration
- Repository cloning with optional GitHub token authentication
- Git pull operations with automatic hot reload triggering
- Supports both public and private repositories

### Web Editor Integration
- Multi-file tabbed editor (main.dart, pubspec.yaml)
- Live Flutter app preview via iframe
- Real-time status updates and compilation feedback

## Environment Variables

- `REPO_URL`: Git repository to clone (optional, creates new Flutter project if not provided)
- `GITHUB_TOKEN`: Authentication token for private repositories (optional)

## Service Architecture Notes

The Dockerfile uses inline configuration for both Nginx and Supervisor rather than separate config files. All services run under Supervisor with:
- Nginx configured for reverse proxy with specific routing rules
- Flask server with auto-restart and log forwarding
- Single port 80 exposure for simplified deployment

## Error Handling Patterns

- API endpoints return JSON with `status` field for success/error indication
- Flutter process errors captured in output buffer for debugging
- Git operations include proper error handling with stderr capture
- File operations include existence checks and exception handling