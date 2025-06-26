# SSE Streaming Architecture: Claude to Frontend

This document contains high-level diagrams showing how Server-Sent Events (SSE) streaming works from Claude API to the frontend interface.

## 1. SSE Connection Flow

```mermaid
sequenceDiagram
    participant FE as Frontend
    participant Flask as Flask Server
    participant LLM as LLM Executor
    participant Claude as Claude API
    
    Note over FE,Claude: SSE Connection Establishment
    
    FE->>Flask: POST /api/stream/chat
    Note right of FE: EventSource connection request
    
    Flask->>Flask: Create SSE Generator
    Flask-->>FE: HTTP 200 + SSE Headers
    Note left of Flask: Content-Type: text/event-stream<br/>Connection: keep-alive
    
    Note over FE,Claude: Streaming Data Flow
    
    Flask->>LLM: execute_stream_with_progress()
    LLM->>Claude: Streaming API Request
    
    loop Real-time Streaming
        Claude-->>LLM: Text Chunk
        LLM-->>Flask: StreamProgress Object
        Flask-->>FE: SSE Event
        Note right of Flask: event: progress<br/>data: {"stage": "generating", "text": "chunk"}
        FE->>FE: Update UI in Real-time
    end
    
    Claude-->>LLM: Stream Complete
    LLM-->>Flask: Final Response
    Flask-->>FE: SSE Complete Event
    Note right of Flask: event: complete<br/>data: {"message": "Stream ended"}
    
    FE->>FE: Close EventSource
```

## 2. SSE Protocol Deep Dive

```mermaid
graph TB
    subgraph "Frontend (Browser)"
        ES[EventSource API]
        UI[User Interface]
        Buffer[Response Buffer]
    end
    
    subgraph "Network Layer"
        HTTP[HTTP Connection]
        SSEStream[SSE Stream]
    end
    
    subgraph "Flask Server"
        Route[SSE Route Handler]
        Generator[SSE Generator Function]
        AsyncLoop[Async Event Loop]
    end
    
    subgraph "LLM Integration"
        LLMExec[LLM Executor]
        StreamMgr[Stream Manager]
        ProgressTracker[Progress Tracker]
    end
    
    subgraph "Claude API"
        ClaudeStream[Claude Streaming API]
        Chunks[Response Chunks]
    end
    
    ES -->|new EventSource()| HTTP
    HTTP -->|GET /api/stream/chat| Route
    Route --> Generator
    Generator --> AsyncLoop
    
    AsyncLoop --> LLMExec
    LLMExec --> StreamMgr
    StreamMgr --> ClaudeStream
    
    ClaudeStream --> Chunks
    Chunks -->|Text Delta| ProgressTracker
    ProgressTracker -->|StreamProgress| Generator
    
    Generator -->|yield SSE Event| SSEStream
    SSEStream -->|event: progress<br/>data: JSON| HTTP
    HTTP -->|EventSource.onmessage| ES
    ES --> Buffer
    Buffer --> UI
    
    style SSEStream fill:#e1f5fe
    style Generator fill:#f3e5f5
    style ClaudeStream fill:#e8f5e8
```

## 3. SSE Event Types and Data Flow

```mermaid
flowchart LR
    subgraph "Claude API Response"
        ClaudeChunk[Text Chunk]
        ClaudeComplete[Response Complete]
        ClaudeError[API Error]
    end
    
    subgraph "LLM Executor Processing"
        ParseChunk[Parse Chunk]
        CreateProgress[Create StreamProgress]
        AccumulateText[Accumulate Response]
    end
    
    subgraph "SSE Event Generation"
        ProgressEvent[event: progress]
        TextEvent[event: text]
        CompleteEvent[event: complete]
        ErrorEvent[event: error]
    end
    
    subgraph "Frontend Event Handling"
        OnProgress[onprogress Handler]
        OnText[ontext Handler]
        OnComplete[oncomplete Handler]
        OnError[onerror Handler]
    end
    
    subgraph "UI Updates"
        ProgressBar[Progress Bar]
        TextStream[Streaming Text]
        StatusIndicator[Status Indicator]
        ErrorDisplay[Error Display]
    end
    
    ClaudeChunk --> ParseChunk
    ParseChunk --> CreateProgress
    CreateProgress --> ProgressEvent
    CreateProgress --> TextEvent
    
    ClaudeComplete --> AccumulateText
    AccumulateText --> CompleteEvent
    
    ClaudeError --> ErrorEvent
    
    ProgressEvent --> OnProgress
    TextEvent --> OnText
    CompleteEvent --> OnComplete
    ErrorEvent --> OnError
    
    OnProgress --> ProgressBar
    OnProgress --> StatusIndicator
    OnText --> TextStream
    OnComplete --> StatusIndicator
    OnError --> ErrorDisplay
    
    style ProgressEvent fill:#e3f2fd
    style TextEvent fill:#e8f5e8
    style CompleteEvent fill:#fff3e0
    style ErrorEvent fill:#ffebee
```

## 4. SSE Message Format

```mermaid
graph TB
    subgraph "SSE Event Structure"
        EventType[event: progress]
        DataField[data: JSON payload]
        Separator[Empty line terminator]
    end
    
    subgraph "Progress Event Data"
        Stage[stage: "analyzing/generating/applying"]
        Message[message: "Human readable status"]
        PartialContent[partial_content: "Current text chunk"]
        ProgressPercent[progress_percent: 0-100]
        Metadata[metadata: Additional context]
    end
    
    subgraph "Text Event Data"
        TextChunk[text: "Real-time text chunk"]
        Accumulated[accumulated: "Full response so far"]
    end
    
    subgraph "Complete Event Data"
        FinalMessage[message: "Stream completed"]
        TotalTokens[token_count: Usage statistics]
        ConversationId[conversation_id: Chat context]
    end
    
    EventType --> DataField
    DataField --> Separator
    
    DataField -.->|progress event| Stage
    DataField -.->|progress event| Message
    DataField -.->|progress event| PartialContent
    DataField -.->|progress event| ProgressPercent
    DataField -.->|progress event| Metadata
    
    DataField -.->|text event| TextChunk
    DataField -.->|text event| Accumulated
    
    DataField -.->|complete event| FinalMessage
    DataField -.->|complete event| TotalTokens
    DataField -.->|complete event| ConversationId
```

## 5. Error Handling and Reconnection

```mermaid
stateDiagram-v2
    [*] --> Connecting: new EventSource()
    
    Connecting --> Connected: Connection established
    Connecting --> ConnectionError: Network failure
    
    Connected --> Streaming: Receiving events
    Connected --> Disconnected: Connection lost
    
    Streaming --> Processing: Parse SSE events
    Streaming --> Disconnected: Network interruption
    
    Processing --> UIUpdate: Update interface
    Processing --> StreamError: Invalid event data
    
    UIUpdate --> Streaming: Continue listening
    
    Disconnected --> Reconnecting: Auto-reconnect (3s delay)
    ConnectionError --> Reconnecting: Retry connection
    StreamError --> ErrorDisplay: Show user error
    
    Reconnecting --> Connected: Reconnection successful
    Reconnecting --> ConnectionFailed: Max retries exceeded
    
    ConnectionFailed --> ManualRetry: User action required
    ManualRetry --> Connecting: User clicks retry
    
    ErrorDisplay --> Streaming: Error acknowledged
    
    state Connected {
        [*] --> Idle
        Idle --> ReceivingData: SSE event arrives
        ReceivingData --> BufferingData: Accumulate chunks
        BufferingData --> Idle: Event processed
    }
    
    state Reconnecting {
        [*] --> WaitingDelay
        WaitingDelay --> AttemptConnection: Delay expired
        AttemptConnection --> [*]: Connection result
    }
```

## 6. Performance Characteristics

```mermaid
graph LR
    subgraph "Latency Profile"
        UserRequest[User Request: 0ms]
        SSEEstablish[SSE Connection: ~50ms]
        FirstChunk[First Claude Chunk: ~200ms]
        StreamingChunks[Streaming Chunks: ~50ms intervals]
        FinalResponse[Complete Response: ~2-10s total]
    end
    
    subgraph "Throughput Metrics"
        ChunkSize[Chunk Size: ~50-200 chars]
        EventFreq[Event Frequency: ~20Hz]
        Bandwidth[Bandwidth: ~1-5KB/s per stream]
        Concurrent[Concurrent Streams: ~10-50 users]
    end
    
    subgraph "Resource Usage"
        Memory[Memory: ~1MB per active stream]
        CPU[CPU: ~2-5% per stream]
        Network[Network: HTTP keep-alive]
        Storage[Storage: Conversation history]
    end
    
    UserRequest --> SSEEstablish
    SSEEstablish --> FirstChunk
    FirstChunk --> StreamingChunks
    StreamingChunks --> FinalResponse
    
    ChunkSize -.-> EventFreq
    EventFreq -.-> Bandwidth
    Bandwidth -.-> Concurrent
    
    Memory -.-> CPU
    CPU -.-> Network
    Network -.-> Storage
    
    style UserRequest fill:#e8f5e8
    style FinalResponse fill:#e3f2fd
    style Concurrent fill:#fff3e0
```

## Summary

The SSE streaming architecture provides:

1. **Real-time Communication**: Unidirectional server-to-client streaming
2. **HTTP-based**: Works with existing web infrastructure
3. **Automatic Reconnection**: Built-in resilience with EventSource API
4. **Efficient Protocol**: Minimal overhead compared to WebSockets
5. **Progress Tracking**: Granular updates during long-running operations
6. **Error Recovery**: Graceful handling of network interruptions

This design is optimal for the live code generation use case where the primary need is streaming AI responses and progress updates from server to client.