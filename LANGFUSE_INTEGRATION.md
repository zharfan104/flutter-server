# Langfuse Integration for LLM Observability

## Overview

The LLM executor now includes comprehensive Langfuse integration for enhanced observability and monitoring of AI model usage throughout the Flutter development server.

## Installation

```bash
pip install langfuse
```

## Features

### 🔍 **Comprehensive Observability**
- **Request Tracking**: Every LLM call is traced with input, output, and metadata
- **Usage Monitoring**: Token usage and costs tracked per request
- **Performance Metrics**: Response times and success rates monitored
- **Error Tracking**: Failed requests logged with detailed error information

### 🏷️ **Detailed Metadata**
- **Provider Information**: Anthropic (Claude) vs OpenAI distinction
- **Model Details**: Specific model versions and configurations
- **Request Context**: Message counts, prompt types, and parameters
- **Session Tracking**: User and session identification for analytics

### 📊 **Usage Analytics**
- **Token Consumption**: Input, output, and total token tracking
- **Cache Performance**: Claude's cache hit/miss statistics
- **Response Quality**: Success rates and error patterns
- **Performance Trends**: Response time analysis over time

## Usage

### Basic Usage with Observability

```python
from code_modification.llm_executor import SimpleLLMExecutor

# Initialize executor (automatically includes Langfuse if available)
executor = SimpleLLMExecutor()

# Execute with user and session tracking
response = executor.execute(
    messages=[{"role": "user", "content": "Fix this Flutter error: ..."}],
    user_id="developer_123",           # Track usage per developer
    session_id="error_recovery_456",   # Group related requests
    system_prompt="You are a Flutter expert assistant"
)

print(f"Response: {response.text}")
print(f"Token usage: {response.usage.input} + {response.usage.output} = {response.usage.input + response.usage.output}")
```

### Error Recovery with Full Tracing

```python
from code_modification.dart_analysis_fixer import DartAnalysisFixer, FixingConfig

# Configure error recovery with observability
config = FixingConfig(
    max_attempts=3,
    enable_commands=True,
    conversation_id="recovery_session_789"  # Links to Langfuse session
)

fixer = DartAnalysisFixer("./project", config)
result = await fixer.fix_all_errors()

# All LLM calls during recovery are automatically traced in Langfuse
print(f"Recovery successful: {result.success}")
print(f"Fixes applied: {result.fixes_applied}")
```

### Chat Integration with Session Tracking

```python
from chat.chat_service import ChatService

# Initialize chat service (LLM executor used internally)
chat_service = ChatService()

# Process chat with user tracking
response = await chat_service.process_message(
    message="Add user authentication to my Flutter app",
    conversation_id="chat_session_101",
    user_context={
        "user_id": "developer_456",
        "project_type": "flutter_mobile"
    }
)

# All LLM interactions are traced with user and session context
```

## Langfuse Dashboard Features

### 📈 **Usage Analytics**
- **Token Consumption Trends**: Track usage over time
- **Cost Analysis**: Monitor spending per user/session
- **Model Performance**: Compare Claude vs OpenAI effectiveness
- **Cache Efficiency**: Monitor Claude's prompt caching performance

### 🔍 **Request Inspection**
- **Full Request Traces**: Input prompts and complete responses
- **Timing Analysis**: Identify slow requests and bottlenecks
- **Error Investigation**: Detailed error logs with context
- **Success Rate Monitoring**: Track model reliability

### 👥 **User Analytics**
- **Developer Usage Patterns**: Who uses the system most
- **Session Analysis**: Long vs short development sessions
- **Feature Usage**: Which AI features are most popular
- **Error Patterns**: Common issues per developer

### 🎯 **Session Grouping**
Error recovery sessions are automatically grouped in Langfuse:
```
Session: error_recovery_456
├── Initial Analysis (claude-sonnet-4)
├── Command Planning (claude-sonnet-4)
├── Fix Generation #1 (claude-sonnet-4)
├── Fix Generation #2 (claude-sonnet-4)
└── Final Validation (claude-sonnet-4)
```

## Configuration

### Environment Variables

```bash
# Langfuse configuration (set these in your environment)
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."
export LANGFUSE_HOST="https://cloud.langfuse.com"  # or your self-hosted instance
```

### Graceful Fallback

The system works seamlessly with or without Langfuse:

```python
# When Langfuse is available
LANGFUSE_AVAILABLE = True  # Automatic detection
# → Full observability with detailed tracing

# When Langfuse is not installed
LANGFUSE_AVAILABLE = False  # Automatic fallback
# → Normal operation without observability overhead
```

## Integration Points

### 🔧 **Error Recovery System**
- Every dart analyze run is traced
- Command executions are logged with outcomes
- AI fix generation attempts are fully tracked
- Recovery success/failure patterns analyzed

### 💬 **Chat System**
- User conversations tracked end-to-end
- Code modification requests linked to sessions
- Response quality and user satisfaction trackable

### 🚀 **Development Workflow**
- Hot reload recovery attempts monitored
- Build failure resolution tracked
- Developer productivity metrics available

## Benefits

### For Developers
- **Transparency**: See exactly what the AI is doing
- **Debugging**: Investigate when AI responses aren't helpful
- **Learning**: Understand which prompts work best

### For Teams
- **Usage Monitoring**: Track team AI usage and costs
- **Performance Analysis**: Identify bottlenecks and optimize
- **Quality Assurance**: Monitor AI response quality over time

### For System Administrators
- **Cost Management**: Detailed token and cost tracking
- **Performance Optimization**: Identify and resolve slow requests
- **Error Analysis**: Systematic investigation of AI failures

## Example Langfuse Traces

### Error Recovery Trace
```json
{
  "session_id": "error_recovery_456",
  "user_id": "developer_123",
  "traces": [
    {
      "name": "llm_execution",
      "type": "span",
      "metadata": {
        "provider": "anthropic",
        "operation": "error_analysis"
      },
      "generations": [
        {
          "name": "claude_completion",
          "model": "claude-sonnet-4-20250514",
          "input": "Analyze these Dart errors: ...",
          "output": "I'll fix these import errors: <shell>flutter pub get</shell>...",
          "usage": {
            "input": 1250,
            "output": 890,
            "total": 2140
          }
        }
      ]
    }
  ]
}
```

### Chat Interaction Trace
```json
{
  "session_id": "chat_session_101",
  "user_id": "developer_456",
  "traces": [
    {
      "name": "chat_processing",
      "type": "span",
      "metadata": {
        "message_type": "code_modification_request",
        "auto_apply": true
      },
      "generations": [
        {
          "name": "claude_completion",
          "model": "claude-sonnet-4-20250514",
          "input": "Add user authentication...",
          "output": "I'll create a complete authentication system...",
          "usage": {
            "input": 2100,
            "output": 1450,
            "total": 3550
          }
        }
      ]
    }
  ]
}
```

## Testing

Run the integration test to verify everything works:

```bash
python test_langfuse_integration.py
```

Expected output when Langfuse is installed:
```
🎉 All tests passed! Langfuse integration is ready.

💡 Langfuse Usage Example:
executor = SimpleLLMExecutor()
response = executor.execute(
    messages=[{'role': 'user', 'content': 'Hello'}],
    user_id='user_123',
    session_id='session_456'
)
```

## Conclusion

The Langfuse integration provides comprehensive observability for the Flutter development server's AI capabilities without impacting performance or reliability. It enables data-driven optimization of AI interactions and provides valuable insights into developer productivity and system usage patterns.

The integration is designed to be:
- **Non-intrusive**: Works with existing code without changes
- **Resilient**: Graceful fallback when Langfuse unavailable
- **Comprehensive**: Tracks all LLM interactions throughout the system
- **Actionable**: Provides insights for optimization and debugging