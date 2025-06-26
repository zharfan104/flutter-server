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

# AI-powered code modification
curl -X POST http://localhost:5000/api/modify-code \
  -H "Content-Type: application/json" \
  -d '{"description": "Add a login button to the home page"}'

# Chat with AI for code assistance
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a new user profile widget"}'

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

## AI-Powered Code Modification System

This server includes a sophisticated AI-powered code modification system that enables natural language code changes:

### Core Components

#### **Code Modification Service** (`code_modification/`)
- **`llm_executor.py`** - LLM integration supporting Claude 4 Sonnet and OpenAI GPT-4
- **`code_modifier.py`** - Main orchestration service for multi-file code modifications
- **`project_analyzer.py`** - Flutter project structure analysis and dependency mapping
- **`iterative_fixer.py`** - Automated error detection and fixing pipeline
- **`dart_analysis.py`** - Dart analyzer integration for syntax validation
- **`build_pipeline.py`** - Complete AI-driven development workflow orchestration
- **`prompt_loader.py`** - YAML-based prompt management system
- **`prompts/`** - Directory containing modular YAML prompt files
  - **`determine_files.yaml`** - Prompt for file analysis and planning
  - **`generate_code.yaml`** - Prompt for code generation with shell command emphasis

#### **Key API Endpoints**
- **`/api/modify-code` (POST)** - Natural language code modification requests
- **`/api/chat` (POST)** - Conversational AI with automatic code modification detection

#### **AI Features**
- **Natural Language Processing**: Convert plain English descriptions into code changes
- **Smart File Detection**: AI determines which files need modification, creation, or deletion based on project analysis
- **Architecture-Aware Generation**: Respects Flutter patterns (BLoC, Provider, Riverpod, etc.)
- **Multi-file Modifications**: Handles complex changes across multiple files with dependency awareness
- **File Operations**: Automatic creation of new files with proper directory structure and deletion of obsolete files
- **Shell Command Execution**: Runs post-modification commands like `flutter pub get`, `dart format`, build runner
- **Validation & Rollback**: Comprehensive syntax validation with automatic rollback on errors
- **Retry Logic**: Multiple attempts for failed file generation with partial success handling

#### **Usage Examples**
```bash
# Natural language modification with file creation/deletion
curl -X POST http://localhost:5000/api/modify-code \
  -H "Content-Type: application/json" \
  -d '{"description": "Add user authentication with email and password login screen"}'

# Complex feature with multiple file operations
curl -X POST http://localhost:5000/api/modify-code \
  -H "Content-Type: application/json" \
  -d '{"description": "Create a shopping cart system with product models, cart service, and checkout screen"}'

# Chat interface with automatic code modification detection
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Remove the old login system and replace it with OAuth authentication"}'

# Modification with retry configuration
curl -X POST http://localhost:5000/api/modify-code \
  -H "Content-Type: application/json" \
  -d '{"description": "Refactor app to use Riverpod state management", "max_retries": 5}'
```

#### **AI Workflow**
1. **Project Analysis**: Analyze Flutter project structure, dependencies, and architecture patterns
2. **File Planning**: AI determines which files to modify, create, or delete based on request
3. **Code Generation**: LLM generates complete, production-ready file contents with retry logic
4. **File Operations**: Create new files with proper directory structure, modify existing files, delete obsolete files
5. **Validation**: Comprehensive syntax checking, balanced braces, proper imports validation
6. **Shell Commands**: Execute post-modification commands (pub get, formatting, build runner)
7. **Rollback Safety**: Automatic backup creation and rollback on validation failures
8. **Hot Reload**: Automatic Flutter hot reload after successful changes

#### **Enhanced Capabilities**
- **Intelligent File Management**: Automatically creates directories, handles file dependencies
- **Production-Ready Code**: Generates complete, syntactically correct Dart code with proper null safety
- **Architecture Preservation**: Maintains existing patterns (Provider, Bloc, Riverpod, etc.)
- **Dependency Management**: Automatically adds required packages and runs pub get
- **Shell Command Integration**: Emphasized use of `<shell>` blocks for package management and formatting
- **Modular Prompt System**: YAML-based prompt management for easy customization and maintenance
- **Error Recovery**: Partial success handling - continues with successfully generated files
- **Comprehensive Logging**: Detailed operation tracking and performance monitoring

#### **Prompt System**
The AI system uses modular YAML-based prompts stored in `code_modification/prompts/`:
- **Maintainable**: Each prompt is a separate YAML file with metadata
- **Customizable**: Easy to modify prompts without changing code
- **Version Control**: Prompts can be versioned and tracked independently
- **Shell Command Emphasis**: Prompts specifically encourage use of shell commands for:
  - Package management (`flutter pub add`, `flutter pub get`)
  - Code formatting (`dart format .`)
  - Build operations (`flutter packages pub run build_runner build`)
  - Project maintenance (`flutter clean`)

## Error Handling Patterns

- API endpoints return JSON with `status` field for success/error indication
- Flutter process errors captured in output buffer for debugging
- Git operations include proper error handling with stderr capture
- File operations include existence checks and exception handling
- AI modifications include rollback mechanisms and comprehensive validation