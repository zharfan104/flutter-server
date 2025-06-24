# Claude to Frontend SSE Flow

Detailed technical diagrams showing the complete data flow from Claude API to frontend UI through SSE streaming.

## 1. Complete Request-Response Flow

```mermaid
sequenceDiagram
    participant User as User
    participant FE as Frontend UI
    participant ES as EventSource
    participant Flask as Flask Server
    participant Gen as SSE Generator
    participant LLM as LLM Executor
    participant Claude as Claude API
    
    Note over User,Claude: User Initiates Code Generation Request
    
    User->>FE: "Add login button to homepage"
    FE->>ES: new EventSource('/api/stream/modify-code')
    
    Note over FE,Flask: SSE Connection Establishment
    ES->>Flask: GET /api/stream/modify-code + POST data
    Flask->>Gen: create generate_sse_stream()
    Gen-->>ES: HTTP 200 OK + SSE headers
    
    Note over ES,Claude: Initial Setup Events
    Gen->>ES: event: connected
    ES->>FE: Connection established
    FE->>User: Show "Processing..." indicator
    
    Note over Gen,Claude: Project Analysis Phase
    Gen->>LLM: analyze project structure
    Gen->>ES: event: progress (analyzing, 10%)
    ES->>FE: Update progress bar
    
    Gen->>LLM: determine target files
    Gen->>ES: event: progress (files determined, 20%)
    ES->>FE: Show target files list
    
    Note over Gen,Claude: Code Generation Phase
    Gen->>LLM: execute_stream_with_progress()
    LLM->>Claude: POST /v1/messages (stream=true)
    
    Note over Claude,FE: Real-time Streaming Loop
    loop Claude Response Streaming
        Claude-->>LLM: {"type": "content_block_delta", "delta": {"text": "import"}}
        LLM-->>Gen: StreamProgress(partial_content="import")
        Gen-->>ES: event: progress + partial text
        ES-->>FE: Display streaming code
        FE-->>User: Real-time code appears
        
        Claude-->>LLM: {"type": "content_block_delta", "delta": {"text": " 'package:flutter"}}
        LLM-->>Gen: StreamProgress(partial_content="import 'package:flutter")
        Gen-->>ES: event: progress + updated text
        ES-->>FE: Update displayed code
        FE-->>User: Code continues streaming
    end
    
    Claude-->>LLM: {"type": "message_stop"}
    LLM-->>Gen: Complete response with full code
    
    Note over Gen,FE: Code Application Phase
    Gen->>Gen: Parse generated files
    Gen->>ES: event: progress (applying changes, 80%)
    ES->>FE: Show "Applying changes..."
    
    Gen->>Gen: Write files to disk
    Gen->>ES: event: progress (files written, 90%)
    ES->>FE: Show "Files updated"
    
    Gen->>Gen: Trigger hot reload
    Gen->>ES: event: progress (hot reload, 95%)
    ES->>FE: Show "Reloading app..."
    
    Note over Gen,FE: Completion
    Gen->>ES: event: result (success + file list)
    ES->>FE: Show success message
    FE->>User: "✅ Login button added successfully!"
    
    Gen->>ES: event: complete
    ES->>FE: Close progress indicators
    ES->>ES: connection.close()
```

## 2. SSE Data Transformation Pipeline

```mermaid
flowchart TD
    subgraph "Claude API Layer"
        ClaudeReq[Claude Streaming Request]
        ClaudeChunk[Content Block Delta]
        ClaudeText["{\\"type\\": \\"content_block_delta\\", \\"delta\\": {\\"text\\": \\"code chunk\\"}}"]
    end
    
    subgraph "LLM Executor Layer"
        ParseResp[Parse Claude Response]
        ExtractText[Extract Text Delta]
        CreateProgress[Create StreamProgress Object]
        ProgressObj["StreamProgress(stage='generating', partial_content='code', progress=45%)"]
    end
    
    subgraph "SSE Generator Layer"
        ReceiveProgress[Receive StreamProgress]
        ConvertSSE[Convert to SSE Format]
        SSEEvent["event: progress\\ndata: {\\"stage\\": \\"generating\\", \\"partial_content\\": \\"code\\"}\\n\\n"]
    end
    
    subgraph "Network Transport"
        HTTPStream[HTTP Response Stream]
        ChunkedEncoding[Transfer-Encoding: chunked]
        SSEHeaders["Content-Type: text/event-stream\\nConnection: keep-alive"]
    end
    
    subgraph "Frontend Layer"
        EventSource[EventSource API]
        MessageEvent[MessageEvent Object]
        ParseJSON[JSON.parse(event.data)]
        UIUpdate[Update React/Vue Components]
    end
    
    ClaudeReq --> ClaudeChunk
    ClaudeChunk --> ClaudeText
    ClaudeText --> ParseResp
    
    ParseResp --> ExtractText
    ExtractText --> CreateProgress
    CreateProgress --> ProgressObj
    
    ProgressObj --> ReceiveProgress
    ReceiveProgress --> ConvertSSE
    ConvertSSE --> SSEEvent
    
    SSEEvent --> HTTPStream
    HTTPStream --> ChunkedEncoding
    ChunkedEncoding --> SSEHeaders
    
    SSEHeaders --> EventSource
    EventSource --> MessageEvent
    MessageEvent --> ParseJSON
    ParseJSON --> UIUpdate
    
    style ClaudeText fill:#e8f5e8
    style ProgressObj fill:#e3f2fd
    style SSEEvent fill:#fff3e0
    style UIUpdate fill:#ffebee
```

## 3. Frontend SSE Event Processing

```mermaid
graph TB
    subgraph "EventSource Setup"
        CreateES[new EventSource('/api/stream/modify-code')]
        SetupHandlers[Setup Event Handlers]
        ConnectionOpen[Connection Opened]
    end
    
    subgraph "Event Type Routing"
        ReceiveEvent[Receive SSE Event]
        CheckType{Event Type?}
        
        ProgressHandler[onprogress Handler]
        TextHandler[ontext Handler]
        ResultHandler[onresult Handler]
        CompleteHandler[oncomplete Handler]
        ErrorHandler[onerror Handler]
    end
    
    subgraph "Progress Event Processing"
        ParseProgress[Parse Progress Data]
        UpdateProgressBar[Update Progress Bar]
        UpdateStatus[Update Status Text]
        ShowPartialContent[Show Streaming Code]
    end
    
    subgraph "Text Event Processing"
        ParseTextChunk[Parse Text Chunk]
        AppendToBuffer[Append to Response Buffer]
        UpdateCodeEditor[Update Code Editor]
        ScrollToEnd[Scroll to Latest Content]
    end
    
    subgraph "Result Event Processing"
        ParseResult[Parse Final Result]
        ShowFilesList[Show Modified Files]
        ShowSuccessMsg[Show Success Message]
        UpdateAppPreview[Update App Preview]
    end
    
    subgraph "Error Handling"
        ParseError[Parse Error Data]
        ShowErrorMsg[Show Error Message]
        RetryButton[Show Retry Button]
        LogError[Log to Console]
    end
    
    CreateES --> SetupHandlers
    SetupHandlers --> ConnectionOpen
    ConnectionOpen --> ReceiveEvent
    
    ReceiveEvent --> CheckType
    
    CheckType -->|progress| ProgressHandler
    CheckType -->|text| TextHandler
    CheckType -->|result| ResultHandler
    CheckType -->|complete| CompleteHandler
    CheckType -->|error| ErrorHandler
    
    ProgressHandler --> ParseProgress
    ParseProgress --> UpdateProgressBar
    ParseProgress --> UpdateStatus
    ParseProgress --> ShowPartialContent
    
    TextHandler --> ParseTextChunk
    ParseTextChunk --> AppendToBuffer
    AppendToBuffer --> UpdateCodeEditor
    UpdateCodeEditor --> ScrollToEnd
    
    ResultHandler --> ParseResult
    ParseResult --> ShowFilesList
    ParseResult --> ShowSuccessMsg
    ParseResult --> UpdateAppPreview
    
    ErrorHandler --> ParseError
    ParseError --> ShowErrorMsg
    ParseError --> RetryButton
    ParseError --> LogError
    
    style ReceiveEvent fill:#e3f2fd
    style UpdateCodeEditor fill:#e8f5e8
    style ShowSuccessMsg fill:#e8f5e8
    style ShowErrorMsg fill:#ffebee
```

## 4. Real-time UI Updates

```mermaid
timeline
    title SSE-Driven UI State Changes
    
    section Connection Phase
        0s    : User clicks "Generate Code"
              : Show loading spinner
              : Disable form inputs
    
    section Analysis Phase  
        0.5s  : Connection established
              : Show "Analyzing project..."
              : Progress bar: 0%
        
        1s    : Files determined
              : Show "Target files: lib/main.dart, lib/widgets/login.dart"
              : Progress bar: 20%
    
    section Generation Phase
        2s    : Code generation started
              : Show "AI is writing code..."
              : Progress bar: 40%
        
        2.5s  : First code chunk
              : Show streaming code editor
              : Display: "import 'package:flutter/material.dart';"
        
        3s    : More code chunks
              : Update code editor
              : Display: Full import statements
        
        4s    : Widget structure
              : Update code editor  
              : Display: LoginButton widget class
        
        6s    : Complete code
              : Show final generated code
              : Progress bar: 70%
    
    section Application Phase
        7s    : Applying changes
              : Show "Writing files to disk..."
              : Progress bar: 80%
        
        8s    : Files written
              : Show "Files updated successfully"
              : Progress bar: 90%
        
        9s    : Hot reload triggered
              : Show "Reloading Flutter app..."
              : Progress bar: 95%
        
        10s   : Success
              : Show "✅ Login button added!"
              : Progress bar: 100%
              : Re-enable form inputs
```

## 5. SSE vs Traditional AJAX Comparison

```mermaid
graph LR
    subgraph "Traditional AJAX Approach"
        A1[User Request] --> A2[POST /api/modify-code]
        A2 --> A3[Wait... 30 seconds]
        A3 --> A4[Complete Response]
        A4 --> A5[Update UI]
        
        style A3 fill:#ffebee
        style A4 fill:#e8f5e8
    end
    
    subgraph "SSE Streaming Approach"
        B1[User Request] --> B2[EventSource Connection]
        B2 --> B3[Immediate Progress: 0%]
        B3 --> B4[Progress Update: 20%]
        B4 --> B5[Streaming Code: Real-time]
        B5 --> B6[Progress Update: 80%]
        B6 --> B7[Complete: 100%]
        
        style B3 fill:#e3f2fd
        style B4 fill:#e3f2fd
        style B5 fill:#e8f5e8
        style B6 fill:#e3f2fd
        style B7 fill:#e8f5e8
    end
    
    subgraph "User Experience"
        UX1[Traditional: Black box waiting]
        UX2[SSE: Real-time feedback]
        
        style UX1 fill:#ffebee
        style UX2 fill:#e8f5e8
    end
    
    A3 -.-> UX1
    B3 -.-> UX2
    B4 -.-> UX2
    B5 -.-> UX2
```

## 6. Error Recovery and Reconnection

```mermaid
stateDiagram-v2
    [*] --> EstablishingConnection: User starts request
    
    EstablishingConnection --> StreamingActive: SSE connected
    EstablishingConnection --> ConnectionFailed: Network error
    
    StreamingActive --> ReceivingData: Events flowing
    StreamingActive --> ConnectionLost: Network interruption
    
    ReceivingData --> ProcessingEvent: Parse SSE event
    ReceivingData --> ConnectionLost: Connection dropped
    
    ProcessingEvent --> UpdatingUI: Valid event
    ProcessingEvent --> EventError: Invalid event data
    
    UpdatingUI --> ReceivingData: Continue streaming
    
    ConnectionLost --> AttemptingReconnect: Auto-reconnect (3s delay)
    ConnectionFailed --> AttemptingReconnect: Retry connection
    
    AttemptingReconnect --> StreamingActive: Reconnected successfully
    AttemptingReconnect --> ReconnectFailed: Max retries exceeded
    
    ReconnectFailed --> ShowRetryButton: Manual intervention
    ShowRetryButton --> EstablishingConnection: User clicks retry
    
    EventError --> ShowErrorMessage: Display error to user
    ShowErrorMessage --> ReceivingData: Continue with next event
    
    state StreamingActive {
        [*] --> ListeningForEvents
        ListeningForEvents --> BufferingData: Event received
        BufferingData --> ProcessingProgress: Progress event
        BufferingData --> ProcessingText: Text event
        BufferingData --> ProcessingResult: Result event
        ProcessingProgress --> ListeningForEvents
        ProcessingText --> ListeningForEvents  
        ProcessingResult --> ListeningForEvents
    }
    
    state ReconnectFailed {
        [*] --> DisplayError
        DisplayError --> EnableRetryUI
        EnableRetryUI --> [*]
    }
```

This comprehensive set of diagrams shows exactly how SSE enables real-time streaming from Claude API all the way to the frontend UI, providing users with immediate feedback and a smooth live code generation experience.