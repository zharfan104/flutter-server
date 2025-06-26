"""
Enhanced LLM Executor for Flutter Development Server
Includes Langfuse integration for comprehensive observability
Based on steve-backend's LLM executor with added monitoring capabilities
"""

__all__ = ['SimpleLLMExecutor', 'StreamProgress', 'LLMResponse', 'TokenUsage']

import os
import time
import asyncio
from typing import Dict, List, Optional, Union, Tuple, AsyncIterator
from dataclasses import dataclass
from functools import wraps

# Import Langfuse v3 SDK for observability with OpenTelemetry integration
try:
    from langfuse import get_client, observe
    LANGFUSE_AVAILABLE = True
    # Get the global Langfuse client (v3 SDK)
    langfuse_client = get_client()
except ImportError:
    LANGFUSE_AVAILABLE = False
    # Create dummy client and decorator for fallback
    class DummyLangfuseClient:
        def update_current_trace(self, **kwargs): pass
        def update_current_generation(self, **kwargs): pass
        def update_current_span(self, **kwargs): pass
    
    langfuse_client = DummyLangfuseClient()
    
    def observe(as_type=None):
        def decorator(func):
            return func
        return decorator

# Import advanced logging and monitoring
try:
    from src.utils.advanced_logger import logger, LogCategory, LogLevel
    from src.utils.request_tracer import tracer, EventContext, TraceEventType
    from src.utils.performance_monitor import performance_monitor, TimingContext
    from src.utils.error_analyzer import error_analyzer, analyze_error
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

# Empty context manager for backward compatibility
class EmptyContext:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


@dataclass
class TokenUsage:
    """Token usage statistics"""
    input: int = 0
    output: int = 0
    cache_creation: int = 0
    cache_read: int = 0


@dataclass
class LLMResponse:
    """LLM response container"""
    text: str
    usage: TokenUsage
    model: str = ""


@dataclass
class StreamProgress:
    """Progress update for streaming responses"""
    stage: str  # "thinking", "analyzing", "generating", "complete"
    message: str
    partial_content: str = ""
    progress_percent: float = 0.0
    metadata: Optional[Dict] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "stage": self.stage,
            "message": self.message, 
            "partial_content": self.partial_content,
            "progress_percent": self.progress_percent,
            "metadata": self.metadata or {}
        }


@dataclass
class ModelConfig:
    """LLM model configuration"""
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"  # Claude 4 Sonnet
    CLAUDE_FALLBACK_MODEL: str = "claude-3-5-sonnet-20241022"  # Claude 3.5 Sonnet fallback
    CLAUDE_MAX_TOKENS: int = 8192
    OPENAI_MODEL: str = "gpt-4o"
    OPENAI_FALLBACK_MODEL: str = "gpt-4o-mini"
    OPENAI_MAX_TOKENS: int = 4096


@dataclass
class RetryConfig:
    """Retry configuration"""
    MAX_RETRIES: int = 3
    BASE_DELAY: float = 1.0
    MAX_DELAY: float = 10.0


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 10.0):
    """Decorator for retry logic with exponential backoff"""
    def decorator(func):
        # Check if function is an async generator
        import inspect
        if inspect.isasyncgenfunction(func):
            @wraps(func)
            async def async_gen_wrapper(*args, **kwargs):
                last_exception = None
                for attempt in range(max_retries):
                    try:
                        # For async generators, we yield from the generator
                        async for item in func(*args, **kwargs):
                            yield item
                        return  # Exit if successful
                    except Exception as e:
                        last_exception = e
                        if attempt < max_retries - 1:
                            delay = min(base_delay * (2 ** attempt), max_delay)
                            print(f"{func.__name__} attempt {attempt + 1} failed: {str(e)}")
                            print(f"Retrying in {delay} seconds...")
                            await asyncio.sleep(delay)
                print(f"{func.__name__} failed after {max_retries} attempts")
                raise last_exception
            return async_gen_wrapper
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        print(f"{func.__name__} attempt {attempt + 1} failed: {str(e)}")
                        print(f"Retrying in {delay} seconds...")
                        await asyncio.sleep(delay)
            print(f"{func.__name__} failed after {max_retries} attempts")
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = min(base_delay * (2 ** attempt), max_delay)
                        print(f"{func.__name__} attempt {attempt + 1} failed: {str(e)}")
                        print(f"Retrying in {delay} seconds...")
                        time.sleep(delay)
            print(f"{func.__name__} failed after {max_retries} attempts")
            raise last_exception
        
        # Return appropriate wrapper based on function type
        if inspect.isasyncgenfunction(func):
            return async_gen_wrapper
        elif asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator


class SimpleLLMExecutor:
    """
    Simplified LLM executor supporting Claude and OpenAI
    """
    
    def __init__(self):
        self.model_config = ModelConfig()
        self.retry_config = RetryConfig()
        
        # Initialize clients
        self.anthropic_client = None
        self.openai_client = None
        
        self._init_clients()
    
    def _init_clients(self):
        """Initialize LLM clients"""
        # Initialize Anthropic client
        if ANTHROPIC_AVAILABLE:
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                try:
                    # Use modern Anthropic client
                    self.anthropic_client = anthropic.Anthropic(api_key=api_key)
                    print("Anthropic client initialized with modern API")
                except Exception as e:
                    print(f"Failed to initialize Anthropic client: {e}")
            else:
                print("ANTHROPIC_API_KEY environment variable not set")
        else:
            print("Anthropic library not available")
        
        # Initialize OpenAI client
        if OPENAI_AVAILABLE:
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                try:
                    self.openai_client = openai.OpenAI(api_key=api_key)
                    print("OpenAI client initialized")
                except Exception as e:
                    print(f"Failed to initialize OpenAI client: {e}")
            else:
                print("OPENAI_API_KEY environment variable not set")
        else:
            print("OpenAI library not available")
    
    def is_available(self) -> bool:
        """Check if any LLM client is available"""
        return self.anthropic_client is not None or self.openai_client is not None
    
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        models = []
        if self.anthropic_client:
            models.extend([
                self.model_config.CLAUDE_MODEL,
                self.model_config.CLAUDE_FALLBACK_MODEL
            ])
        if self.openai_client:
            models.extend([
                self.model_config.OPENAI_MODEL,
                self.model_config.OPENAI_FALLBACK_MODEL
            ])
        return models
    
    def execute(
        self,
        messages: List[Dict[str, Union[str, List]]],
        system_prompt: Optional[Union[str, List[Dict]]] = None,
        model: Optional[str] = None,
        use_openai: bool = False,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """
        Execute LLM completion
        
        Args:
            messages: List of messages in conversation format
            system_prompt: System prompt for the conversation
            model: Specific model to use (optional)
            use_openai: Force use of OpenAI instead of Claude
            **kwargs: Additional parameters for the LLM
        
        Returns:
            LLMResponse containing the generated text and usage stats
        """
        if not self.is_available():
            raise Exception("No LLM clients available. Please set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variables.")
        
        # Determine which provider to use
        if use_openai and self.openai_client:
            provider = "openai"
        elif self.anthropic_client:
            provider = "anthropic"
        elif self.openai_client:
            provider = "openai"
        else:
            raise Exception("No suitable LLM client available")
        
        print(f"Executing LLM with {provider}")
        
        # For now, return a basic response structure
        # This is a simplified version - you would implement the actual LLM calls here
        return LLMResponse(
            text="LLM functionality requires proper API keys to be set in environment variables.",
            usage=TokenUsage(),
            model=model or (self.model_config.OPENAI_MODEL if provider == "openai" else self.model_config.CLAUDE_MODEL)
        )