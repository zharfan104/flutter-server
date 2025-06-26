# Code Modification Module - Mermaid Architecture Diagrams

## 1. Overall System Architecture

```mermaid
graph TB
    subgraph "API Layer"
        R[Router<br/>router.py]
        R --> |"/api/modify-code"| CM
        R --> |"/api/stream/modify-code"| CM
        R --> |"/api/project-structure"| PA
        R --> |"/api/validate-code"| DA
    end

    subgraph "Service Layer"
        CM[Code Modification Service<br/>code_modifier.py]
        LE[LLM Executor<br/>llm_executor.py]
        PA[Project Analyzer<br/>project_analyzer.py]
        PL[Prompt Loader<br/>prompt_loader.py]
        CE[Command Executor<br/>command_executor.py]
        DA[Dart Analysis<br/>dart_analysis.py]
        HRR[Hot Reload Recovery<br/>hot_reload_recovery.py]
    end

    subgraph "Infrastructure Layer"
        FM[Flutter Manager]
        CHM[Chat Manager]
        AL[Advanced Logger]
        PM[Performance Monitor]
        RT[Request Tracer]
    end

    subgraph "External Services"
        CLAUDE[Claude 4 Sonnet]
        GPT[OpenAI GPT-4]
        LF[Langfuse]
    end

    subgraph "Prompt System"
        P1[determine_files.yaml]
        P2[generate_code.yaml]
        P3[error_analysis.yaml]
        P4[validation.yaml]
        P5[architecture_analysis.yaml]
        PN[... 12 more prompts]
    end

    CM --> LE
    CM --> PA
    CM --> CE
    CM --> DA
    CM --> HRR
    LE --> PL
    PL --> P1
    PL --> P2
    PL --> P3
    PL --> P4
    PL --> P5
    PL --> PN
    LE --> CLAUDE
    LE --> GPT
    LE --> LF
    CM --> FM
    CM --> CHM
    R --> AL
    R --> PM
    R --> RT

    style R fill:#e1f5fe
    style CM fill:#f3e5f5
    style LE fill:#fff3e0
    style PA fill:#e8f5e8
```

## 2. Code Modification Workflow

```mermaid
sequenceDiagram
    participant U as User
    participant R as Router
    participant CM as CodeModificationService
    participant PA as ProjectAnalyzer
    participant PL as PromptLoader
    participant LE as LLMExecutor
    participant CE as CommandExecutor
    participant FM as FlutterManager

    U->>R: POST /api/modify-code
    R->>CM: modify_code_request()
    
    CM->>PA: analyze_project()
    PA-->>CM: ProjectStructure
    
    CM->>PL: load_prompt("determine_files")
    PL-->>CM: File Analysis Prompt
    
    CM->>LE: execute_llm(file_analysis)
    LE-->>CM: Files to Modify List
    
    loop For each file
        CM->>PL: load_prompt("generate_code")
        PL-->>CM: Code Generation Prompt
        CM->>LE: execute_llm(code_generation)
        LE-->>CM: Generated Code
        CM->>CM: validate_code()
        CM->>FM: write_file()
    end
    
    CM->>CE: execute_commands(["flutter pub get"])
    CE-->>CM: Command Results
    
    CM->>FM: trigger_hot_reload()
    FM-->>CM: Hot Reload Status
    
    CM-->>R: ModificationResult
    R-->>U: JSON Response
```

## 3. Streaming Architecture

```mermaid
graph LR
    subgraph "Client Side"
        C[Client Browser]
        ES[EventSource]
    end

    subgraph "Server Side"
        R[Router]
        CM[CodeModificationService]
        SP[StreamProgress]
        LE[LLMExecutor]
    end

    C --> ES
    ES --> |SSE Connection| R
    R --> |"/api/stream/modify-code"| CM
    CM --> SP
    SP --> LE
    LE --> |Streaming Response| SP
    SP --> |Progress Events| CM
    CM --> |yield progress| R
    R --> |Server-Sent Events| ES
    ES --> |Real-time Updates| C

    style ES fill:#e3f2fd
    style SP fill:#fff3e0
    style CM fill:#f3e5f5
```

## 4. LLM Executor Architecture

```mermaid
graph TB
    subgraph "LLM Executor"
        SLE[SimpleLLMExecutor]
        SP[StreamProgress]
        LR[LLMResponse]
        TU[TokenUsage]
    end

    subgraph "Provider Management"
        CP[Claude Provider]
        OP[OpenAI Provider]
        FB[Fallback Logic]
    end

    subgraph "Observability"
        LF[Langfuse Integration]
        PM[Performance Metrics]
        RL[Retry Logic]
    end

    subgraph "External APIs"
        CLAUDE[Claude 4 Sonnet]
        SONNET[Claude 3.5 Sonnet]
        GPT4[GPT-4 Turbo]
        GPT35[GPT-3.5 Turbo]
    end

    SLE --> CP
    SLE --> OP
    SLE --> FB
    SLE --> SP
    SLE --> LR
    SLE --> TU
    
    CP --> CLAUDE
    CP --> SONNET
    OP --> GPT4
    OP --> GPT35
    
    SLE --> LF
    SLE --> PM
    SLE --> RL

    style SLE fill:#fff3e0
    style CP fill:#e8f5e8
    style OP fill:#fce4ec
    style LF fill:#f3e5f5
```

## 5. Project Analysis Flow

```mermaid
flowchart TD
    PA[Project Analyzer] --> PY[Parse pubspec.yaml]
    PA --> DF[Scan Dart Files]
    PA --> SD[Analyze Structure]
    
    PY --> DEP[Extract Dependencies]
    PY --> META[Project Metadata]
    
    DF --> IMP[Parse Imports]
    DF --> CLS[Extract Classes]
    DF --> WID[Find Widgets]
    
    SD --> ARCH[Detect Architecture]
    SD --> PAT[Identify Patterns]
    
    DEP --> PS[Project Structure]
    META --> PS
    IMP --> PS
    CLS --> PS
    WID --> PS
    ARCH --> PS
    PAT --> PS
    
    PS --> CM[Code Modification Service]

    stylePA fill:#e8f5e8
    style PS fill:#fff3e0
    style CM fill:#f3e5f5
```

## 6. Error Recovery System

```mermaid
stateDiagram-v2
    [*] --> CompilationError
    CompilationError --> AnalyzeErrors
    AnalyzeErrors --> DartAnalysis
    DartAnalysis --> ErrorCategorization
    
    ErrorCategorization --> CriticalErrors
    ErrorCategorization --> CompilationErrors
    ErrorCategorization --> ImportErrors
    ErrorCategorization --> TypeErrors
    
    CriticalErrors --> GenerateFixes
    CompilationErrors --> GenerateFixes
    ImportErrors --> GenerateFixes
    TypeErrors --> GenerateFixes
    
    GenerateFixes --> ApplyFixes
    ApplyFixes --> ValidateCode
    ValidateCode --> Success
    ValidateCode --> RetryFix
    
    RetryFix --> AnalyzeErrors
    RetryFix --> FallbackRecovery
    FallbackRecovery --> [*]
    Success --> [*]

    note right of DartAnalysis
        Uses dart analyze command
        Structured error parsing
        Severity assessment
    end note
    
    note right of GenerateFixes
        LLM-powered fix generation
        Context-aware solutions
        Targeted code changes
    end note
```

## 7. Prompt System Architecture

```mermaid
graph TB
    subgraph "Prompt Categories"
        subgraph "Core Prompts"
            DF[determine_files.yaml]
            GC[generate_code.yaml]
        end
        
        subgraph "Analysis Prompts"
            EA[error_analysis.yaml]
            AA[architecture_analysis.yaml]
            VAL[validation.yaml]
        end
        
        subgraph "Specialized Prompts"
            REF[refactoring.yaml]
            TEST[testing.yaml]
            PERF[performance_optimization.yaml]
        end
        
        subgraph "Infrastructure Prompts"
            DM[dependency_management.yaml]
            SCE[shell_command_executor.yaml]
            CER[comprehensive_error_recovery.yaml]
        end
    end
    
    PL[Prompt Loader] --> DF
    PL --> GC
    PL --> EA
    PL --> AA
    PL --> VAL
    PL --> REF
    PL --> TEST
    PL --> PERF
    PL --> DM
    PL --> SCE
    PL --> CER
    
    PL --> PS[Parameter Substitution]
    PS --> FP[Formatted Prompt]
    FP --> LE[LLM Executor]

    style PL fill:#fff3e0
    style PS fill:#e8f5e8
    style FP fill:#f3e5f5
```

## 8. Command Execution Security

```mermaid
flowchart TD
    CE[Command Executor] --> VAL[Validate Command]
    VAL --> WL{Whitelisted?}
    
    WL -->|Yes| SA[Sanitize Arguments]
    WL -->|No| REJ[Reject Command]
    
    SA --> RF{Required Files?}
    RF -->|Check Passed| EX[Execute Command]
    RF -->|Missing Files| ERR[Return Error]
    
    EX --> TO[Apply Timeout]
    TO --> LOG[Log Execution]
    LOG --> RES[Return Result]
    
    REJ --> LOG
    ERR --> LOG

    style VAL fill:#ffebee
    style WL fill:#fff3e0
    style EX fill:#e8f5e8
    style LOG fill:#f3e5f5
```

## 9. File Operation Flow

```mermaid
sequenceDiagram
    participant CM as CodeModificationService
    participant VAL as Validator
    participant BU as Backup
    participant FM as FlutterManager
    participant FS as FileSystem

    CM->>VAL: validate_dart_code()
    VAL-->>CM: Validation Result
    
    alt Validation Passed
        CM->>BU: create_backup()
        BU->>FS: backup_files()
        BU-->>CM: Backup Created
        
        CM->>FM: write_files()
        FM->>FS: write_file_content()
        FS-->>FM: Write Success
        FM-->>CM: Files Written
        
        CM->>FM: trigger_hot_reload()
        FM-->>CM: Hot Reload Status
    else Validation Failed
        CM->>CM: log_validation_errors()
        CM-->>CM: Skip File Operations
    end
    
    alt Hot Reload Failed
        CM->>BU: restore_backup()
        BU->>FS: restore_files()
        BU-->>CM: Backup Restored
    end
```

## 10. Monitoring and Observability

```mermaid
graph TB
    subgraph "Request Lifecycle"
        REQ[Incoming Request]
        PROC[Processing]
        RESP[Response]
    end
    
    subgraph "Monitoring Components"
        RT[Request Tracer]
        AL[Advanced Logger]
        PM[Performance Monitor]
        EA[Error Analyzer]
    end
    
    subgraph "External Observability"
        LF[Langfuse]
        METRICS[Metrics Store]
        ALERTS[Alert System]
    end
    
    REQ --> RT
    REQ --> AL
    PROC --> PM
    PROC --> EA
    RESP --> RT
    RESP --> AL
    
    RT --> METRICS
    AL --> METRICS
    PM --> METRICS
    EA --> ALERTS
    
    PM --> LF
    AL --> LF

    style RT fill:#e3f2fd
    style AL fill:#fff3e0
    style PM fill:#e8f5e8
    style EA fill:#ffebee
```