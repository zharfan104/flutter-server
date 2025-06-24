# Flutter Development Server

A containerized Flutter development environment with AI-powered code modification capabilities. This server combines multiple services into a single Docker container and provides a modern web-based interface for Flutter development.

## 🚀 Features

- **Flutter Development Server** with hot reload capabilities
- **AI-Powered Code Modification** using Claude/OpenAI
- **Real-time Streaming Responses** with token-by-token chat and live code generation
- **Web-Based Code Editor** with Monaco Editor and Dart syntax support
- **Project Analysis** with Flutter-specific insights
- **Real-time Chat Interface** for conversational code assistance
- **Nginx Reverse Proxy** for seamless routing
- **Bootstrap UI** with responsive design

## 📋 Prerequisites

- Python 3.8.1 or higher
- Poetry (Python package manager)
- Flutter SDK (for local development)
- Docker (for containerized deployment)

## 🔧 Environment Setup

### Required Environment Variables

Create a `.env` file in the project root or set these environment variables:

```bash
# AI/LLM Configuration (Required for chat features)
ANTHROPIC_API_KEY=your_anthropic_api_key_here    # Primary AI service
OPENAI_API_KEY=your_openai_api_key_here          # Alternative/fallback AI service (optional)

# Flutter Project Configuration (Optional)
REPO_URL=https://github.com/user/repo.git       # Git repository to clone
GITHUB_TOKEN=your_github_token_here              # For private repositories
```

### Getting API Keys

#### Anthropic API Key (Recommended)
1. Visit [console.anthropic.com](https://console.anthropic.com)
2. Create an account or sign in
3. Navigate to "API Keys" section
4. Generate a new API key
5. Copy the key and set it as `ANTHROPIC_API_KEY`

#### OpenAI API Key (Alternative)
1. Visit [platform.openai.com](https://platform.openai.com)
2. Create an account or sign in
3. Go to "API Keys" section
4. Create a new secret key
5. Copy the key and set it as `OPENAI_API_KEY`

### Security Best Practices

- **Never commit API keys** to version control
- Use `.env` files for local development
- Use secure environment variable management in production
- Regularly rotate API keys
- Monitor API usage and set billing limits

## 🛠 Installation & Setup

### Local Development with Poetry

```bash
# Clone the repository
git clone <repository-url>
cd flutter-server

# Install dependencies
poetry install

# Create environment file
cp .env.example .env
# Edit .env with your API keys

# Activate Poetry environment
poetry shell

# Run the development server
python run.py
```

### Alternative: Run with Poetry directly

```bash
# Set environment variables (Linux/Mac)
export ANTHROPIC_API_KEY="your_key_here"
export REPO_URL="https://github.com/user/repo.git"

# Set environment variables (Windows)
set ANTHROPIC_API_KEY=your_key_here
set REPO_URL=https://github.com/user/repo.git

# Run with Poetry
poetry run python run.py
```

### Docker Development (Legacy)

```bash
# Build Docker image
docker build -t flutter-server .

# Run container with environment variables
docker run -p 80:80 \
  -e ANTHROPIC_API_KEY=your_key_here \
  -e REPO_URL=https://github.com/user/repo.git \
  flutter-server
```

## 🌐 Access URLs

Once running, access the application at:

- **Main Dashboard**: http://localhost:5000
- **Code Editor**: http://localhost:5000/editor
- **AI Chat**: http://localhost:5000/chat
- **Project Overview**: http://localhost:5000/project
- **Flutter App**: http://localhost:5000/app
- **API Health**: http://localhost:5000/api/health

## 🤖 AI Chat Features

The AI chat interface provides conversational assistance for Flutter development:

### Capabilities
- **Code Generation**: "Create a new login screen with email and password fields"
- **Code Modification**: "Add dark mode support to the app"
- **Bug Fixing**: "Fix the error in my authentication logic"
- **Architecture Advice**: "How should I structure my state management?"
- **Package Recommendations**: "What's the best package for HTTP requests?"

### Chat Commands
- Natural language requests for code changes
- Project analysis and suggestions
- Real-time code modification with hot reload
- Multi-file modifications
- Automatic Flutter project understanding

### Example Conversations
```
User: "Add a floating action button that opens a new screen"
AI: I'll help you add a floating action button. Let me analyze your current project structure and create the necessary components...

User: "The app is crashing when I navigate to the profile page"
AI: I can help debug that issue. Let me examine your navigation code and identify the problem...
```

## 📁 Project Structure

```
flutter-server/
├── templates/              # HTML templates
│   ├── base.html           # Base template with navigation
│   ├── index.html          # Main dashboard
│   ├── editor.html         # Code editor interface
│   ├── chat.html           # AI chat interface
│   └── project.html        # Project overview
├── static/                 # Static assets
│   ├── css/               # Custom styles
│   └── js/                # JavaScript modules
├── code_modification/      # AI code modification system
│   ├── llm_executor.py    # LLM integration
│   ├── project_analyzer.py # Flutter project analysis
│   └── code_modifier.py   # Multi-file modifications
├── utils/                 # Utility modules
│   ├── file_operations.py # File management
│   └── status_tracker.py  # Progress tracking
├── chat/                  # Chat system (in-memory)
│   └── chat_manager.py    # Conversation management
├── flutter_server.py     # Main Flask application
├── run.py                # Development server entry point
└── pyproject.toml        # Python dependencies
```

## 🔧 API Endpoints

### Core Flutter APIs
- `POST /api/start` - Start Flutter development server
- `GET /api/status` - Get Flutter process status
- `POST /api/hot-reload` - Trigger hot reload
- `PUT /api/file/<path>` - Update file content
- `GET /api/file/<path>` - Get file content

### AI Code Modification APIs
- `POST /api/modify-code` - Request AI code modification
- `GET /api/modify-status/<id>` - Check modification progress
- `POST /api/analyze-project` - Analyze Flutter project
- `POST /api/suggest-files` - Get file suggestions for changes

### Chat APIs
- `POST /api/chat/send` - Send chat message (non-streaming)
- `POST /api/stream/chat` - **NEW: Stream chat responses in real-time**
- `GET /api/chat/history` - Get conversation history
- `POST /api/chat/new` - Start new conversation

### Streaming APIs (NEW!)
- `POST /api/stream/chat` - Real-time token-by-token chat responses
- `POST /api/stream/modify-code` - Live code generation with progress updates
- `GET /streaming-demo` - Interactive demo of streaming capabilities

See [STREAMING_API.md](STREAMING_API.md) for detailed streaming documentation.

## 🚀 Cloud Deployment

```bash
# Deploy to Google Cloud Build
python build.py
```

## 🧪 Development Workflow

1. **Start the server**: `poetry run python run.py`
2. **Open browser**: Navigate to http://localhost:5000
3. **Start chatting**: Use the AI chat for code assistance
4. **Edit code**: Use the integrated code editor
5. **See changes**: Flutter hot reload shows updates instantly

## 🔧 Configuration

### Environment Variables Reference

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `ANTHROPIC_API_KEY` | Yes* | Claude AI API key | `sk-ant-api03-...` |
| `OPENAI_API_KEY` | No | OpenAI API key (fallback) | `sk-...` |
| `REPO_URL` | No | Git repository to clone | `https://github.com/user/repo.git` |
| `GITHUB_TOKEN` | No | GitHub token for private repos | `ghp_...` |

*Required for AI chat features

### .env File Example

```bash
# Copy this to .env and fill in your values
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
OPENAI_API_KEY=sk-your-openai-key-here
REPO_URL=https://github.com/yourusername/your-flutter-project.git
GITHUB_TOKEN=ghp_your-github-token-here
```

## 🐛 Troubleshooting

### Common Issues

#### "API key not found" Error
- Ensure `ANTHROPIC_API_KEY` is set correctly
- Check for typos in the API key
- Verify the API key is active on Anthropic console

#### Flutter not starting
- Ensure Flutter SDK is installed
- Check Flutter version compatibility
- Verify port 8080 is available

#### Chat not responding
- Check API key configuration
- Verify internet connection
- Check server logs for LLM errors

#### Hot reload not working
- Ensure Flutter process is running
- Check for Dart syntax errors
- Verify file permissions

### Debug Mode

Run with debug logging:
```bash
FLASK_DEBUG=1 poetry run python run.py
```

## 📚 Additional Resources

- [Flutter Documentation](https://docs.flutter.dev/)
- [Anthropic API Documentation](https://docs.anthropic.com/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Poetry Documentation](https://python-poetry.org/docs/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Happy Flutter Development with AI! 🚀✨**