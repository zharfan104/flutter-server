# Streaming API Documentation

The Flutter Server now supports real-time streaming responses for both chat and code modification endpoints using Server-Sent Events (SSE).

## Overview

Streaming provides:
- **Real-time token-by-token chat responses** - See AI responses as they're generated
- **Live progress updates** - Track code generation and modification progress
- **Partial content preview** - Preview generated code before completion
- **Better UX** - Immediate feedback instead of waiting for complete responses

## Streaming Endpoints

### 1. Chat Streaming: `/api/stream/chat`

Real-time chat responses with token-by-token streaming.

**Request:**
```bash
curl -X POST http://localhost:5000/api/stream/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I implement state management in Flutter?",
    "conversation_id": "optional-conversation-id",
    "user_id": "user123"
  }'
```

**Response Events:**

1. **Connected Event**
```
event: connected
data: {"message": "Connected to chat stream"}
```

2. **Progress Events**
```
event: progress
data: {
  "stage": "analyzing",
  "message": "Understanding your request...",
  "progress_percent": 20.0
}
```

3. **Text Streaming Events** (New!)
```
event: text
data: {
  "text": "To implement state management",
  "accumulated": "To implement state management"
}
```

4. **Chat Response Event**
```
event: chat_response
data: {
  "message": "Complete response text...",
  "conversation_id": "conv-123",
  "intent": "question",
  "metadata": {
    "streamed": true,
    "token_count": 150
  }
}
```

5. **Complete Event**
```
event: complete
data: {"message": "Chat stream ended"}
```

### 2. Code Modification Streaming: `/api/stream/modify-code`

Live code generation with file-by-file progress tracking.

**Request:**
```bash
curl -X POST http://localhost:5000/api/stream/modify-code \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Create a login screen with email and password fields",
    "user_id": "user123"
  }'
```

**Response Events:**

1. **File Generation Progress**
```
event: progress
data: {
  "stage": "generating",
  "message": "Generating lib/screens/login_screen.dart...",
  "progress_percent": 45.0,
  "partial_content": "class LoginScreen extends...",
  "metadata": {
    "current_file": "lib/screens/login_screen.dart",
    "streaming": true
  }
}
```

2. **File Complete Events**
```
event: progress
data: {
  "stage": "generating",
  "message": "Completed lib/screens/login_screen.dart",
  "progress_percent": 50.0,
  "metadata": {
    "current_file": "lib/screens/login_screen.dart",
    "file_complete": true
  }
}
```

3. **Result Event**
```
event: result
data: {
  "event_type": "result",
  "success": true,
  "modified_files": ["lib/main.dart"],
  "created_files": ["lib/screens/login_screen.dart"],
  "commands_executed": ["flutter pub get"],
  "request_id": "req-123"
}
```

## JavaScript Client Example

### Basic SSE Connection
```javascript
// Using fetch API for POST with streaming
async function streamChat(message) {
    const response = await fetch('/api/stream/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message: message,
            conversation_id: currentConversationId
        })
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const data = JSON.parse(line.slice(6));
                handleStreamEvent(data);
            }
        }
    }
}

function handleStreamEvent(data) {
    if (data.event_type === 'text') {
        // Append text chunk to UI
        appendToMessage(data.text);
    } else if (data.event_type === 'chat_response') {
        // Finalize the message
        finalizeMessage(data);
    } else if (data.stage) {
        // Update progress indicator
        updateProgress(data);
    }
}
```

### Advanced Streaming with Progress
```javascript
class StreamingChatManager {
    constructor() {
        this.currentStreamingMessage = null;
        this.currentStreamingContent = '';
    }

    async sendMessageWithStreaming(message) {
        // Show user message immediately
        this.addUserMessage(message);
        
        // Start streaming AI response
        const response = await fetch('/api/stream/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        // Create placeholder for AI message
        this.createStreamingMessage();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = JSON.parse(line.slice(6));
                    
                    if (data.event_type === 'text') {
                        // Real-time text streaming
                        this.appendStreamingText(data.text);
                    } else if (data.event_type === 'chat_response') {
                        // Complete message received
                        this.finalizeStreamingMessage(data);
                    }
                }
            }
        }
    }

    appendStreamingText(text) {
        this.currentStreamingContent += text;
        if (this.currentStreamingMessage) {
            this.currentStreamingMessage.innerHTML = this.formatMessage(this.currentStreamingContent) + '<span class="typing-cursor">▌</span>';
        }
    }

    finalizeStreamingMessage(data) {
        if (this.currentStreamingMessage) {
            // Remove cursor and finalize content
            this.currentStreamingMessage.innerHTML = this.formatMessage(data.message);
            this.currentStreamingMessage = null;
            this.currentStreamingContent = '';
        }
    }
}
```

## Progress Stages

The streaming API uses these progress stages:

- **`thinking`** - Initial processing (0-20%)
- **`analyzing`** - Understanding request and analyzing project (20-40%)
- **`generating`** - Generating code or response (40-80%)
- **`applying`** - Applying changes to files (80-95%)
- **`complete`** - Process completed (100%)
- **`error`** - Error occurred

## Benefits

1. **Improved User Experience**
   - Immediate feedback when sending messages
   - See responses as they're generated
   - Track progress of long operations

2. **Better Error Handling**
   - Know exactly where failures occur
   - Partial results on errors
   - Real-time error messages

3. **Resource Efficiency**
   - No polling required
   - Single connection for entire operation
   - Automatic connection management

## Migration Guide

To migrate from non-streaming to streaming endpoints:

1. **Change endpoint URL**
   - `/api/chat/send` → `/api/stream/chat`
   - `/api/modify-code` → `/api/stream/modify-code`

2. **Update response handling**
   - Replace `.json()` parsing with streaming reader
   - Handle multiple event types instead of single response
   - Add UI updates for partial content

3. **Add progress indicators**
   - Show typing indicators during streaming
   - Display progress bars for code generation
   - Update UI incrementally

## Demo

Visit `/streaming-demo` to see a live demonstration of the streaming capabilities with:
- Real-time text generation
- Progress tracking
- File-by-file code generation
- Error handling examples

## Technical Details

- Uses Server-Sent Events (SSE) over HTTP
- Supports POST requests with JSON bodies
- Automatic reconnection on connection loss
- UTF-8 text encoding for all events
- Chunked transfer encoding for efficiency