"""
Command Executor Service
Handles safe execution of Flutter/Dart commands with comprehensive logging
"""

import subprocess
import os
import time
import json
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Import advanced logging and monitoring
try:
    from src.utils.advanced_logger import logger, LogCategory, LogLevel
    from src.utils.performance_monitor import performance_monitor, TimingContext
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False


class CommandType(Enum):
    """Types of commands that can be executed"""
    FLUTTER_PUB = "flutter_pub"
    DART_ANALYZE = "dart_analyze"
    DART_FIX = "dart_fix"
    DART_FORMAT = "dart_format"
    BUILD_RUNNER = "build_runner"
    FLUTTER_CLEAN = "flutter_clean"
    FLUTTER_DOCTOR = "flutter_doctor"


@dataclass
class CommandResult:
    """Result of command execution"""
    success: bool
    command: str
    args: List[str]
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    error_message: Optional[str] = None
    timeout: bool = False


@dataclass
class CommandConfig:
    """Configuration for a command"""
    command_type: CommandType
    base_command: List[str]
    timeout: int
    description: str
    allowed_args: List[str] = None
    required_files: List[str] = None


class CommandExecutor:
    """
    Safe executor for Flutter/Dart commands with comprehensive logging
    """
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.command_configs = self._init_command_configs()
        
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.SYSTEM, "CommandExecutor initialized", 
                       context={"project_path": str(project_path)})
    
    def _init_command_configs(self) -> Dict[CommandType, CommandConfig]:
        """Initialize allowed command configurations"""
        return {
            CommandType.FLUTTER_PUB: CommandConfig(
                command_type=CommandType.FLUTTER_PUB,
                base_command=["flutter", "pub"],
                timeout=180,  # 3 minutes
                description="Flutter package management",
                allowed_args=["get", "add", "remove", "upgrade", "deps", "pub", "run"],
                required_files=["pubspec.yaml"]
            ),
            CommandType.DART_ANALYZE: CommandConfig(
                command_type=CommandType.DART_ANALYZE,
                base_command=["dart", "analyze"],
                timeout=60,  # 1 minute
                description="Dart static analysis",
                allowed_args=["--fatal-infos", "--fatal-warnings", "--no-fatal-warnings"],
                required_files=[]
            ),
            CommandType.DART_FIX: CommandConfig(
                command_type=CommandType.DART_FIX,
                base_command=["dart", "fix"],
                timeout=60,  # 1 minute
                description="Dart automatic fixing",
                allowed_args=["--apply", "--dry-run"],
                required_files=[]
            ),
            CommandType.DART_FORMAT: CommandConfig(
                command_type=CommandType.DART_FORMAT,
                base_command=["dart", "format"],
                timeout=30,  # 30 seconds
                description="Dart code formatting",
                allowed_args=["--fix", "--set-exit-if-changed"],
                required_files=[]
            ),
            CommandType.BUILD_RUNNER: CommandConfig(
                command_type=CommandType.BUILD_RUNNER,
                base_command=["flutter", "packages", "pub", "run", "build_runner"],
                timeout=300,  # 5 minutes
                description="Build runner code generation",
                allowed_args=["build", "clean", "watch"],
                required_files=["pubspec.yaml"]
            ),
            CommandType.FLUTTER_CLEAN: CommandConfig(
                command_type=CommandType.FLUTTER_CLEAN,
                base_command=["flutter", "clean"],
                timeout=60,  # 1 minute
                description="Flutter project cleanup",
                allowed_args=[],
                required_files=["pubspec.yaml"]
            ),
            CommandType.FLUTTER_DOCTOR: CommandConfig(
                command_type=CommandType.FLUTTER_DOCTOR,
                base_command=["flutter", "doctor"],
                timeout=30,  # 30 seconds
                description="Flutter environment check",
                allowed_args=["--verbose", "-v"],
                required_files=[]
            )
        }
    
    async def execute_command(self, command_type: CommandType, args: List[str] = None, 
                            target_path: Optional[str] = None) -> CommandResult:
        """
        Execute a command safely with comprehensive logging
        
        Args:
            command_type: Type of command to execute
            args: Additional arguments for the command
            target_path: Specific target path (relative to project root)
            
        Returns:
            CommandResult with execution details
        """
        start_time = time.time()
        
        if command_type not in self.command_configs:
            error_msg = f"Unknown command type: {command_type}"
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.SHELL_CMD, error_msg)
            return CommandResult(
                success=False,
                command=str(command_type),
                args=args or [],
                exit_code=-1,
                stdout="",
                stderr="",
                execution_time=0,
                error_message=error_msg
            )
        
        config = self.command_configs[command_type]
        
        # Validate arguments
        if args:
            invalid_args = [arg for arg in args if config.allowed_args and arg not in config.allowed_args]
            if invalid_args:
                error_msg = f"Invalid arguments for {command_type}: {invalid_args}"
                if MONITORING_AVAILABLE:
                    logger.error(LogCategory.SHELL_CMD, error_msg)
                return CommandResult(
                    success=False,
                    command=str(command_type),
                    args=args,
                    exit_code=-1,
                    stdout="",
                    stderr="",
                    execution_time=0,
                    error_message=error_msg
                )
        
        # Check required files
        for required_file in config.required_files:
            if not (self.project_path / required_file).exists():
                error_msg = f"Required file missing for {command_type}: {required_file}"
                if MONITORING_AVAILABLE:
                    logger.error(LogCategory.SHELL_CMD, error_msg)
                return CommandResult(
                    success=False,
                    command=str(command_type),
                    args=args or [],
                    exit_code=-1,
                    stdout="",
                    stderr="",
                    execution_time=0,
                    error_message=error_msg
                )
        
        # Build full command
        full_command = config.base_command.copy()
        if args:
            full_command.extend(args)
        if target_path:
            full_command.append(str(self.project_path / target_path))
        
        command_str = " ".join(full_command)
        
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.SHELL_CMD, f"Executing: {command_str}",
                       context={
                           "command_type": command_type.value,
                           "description": config.description,
                           "timeout": config.timeout,
                           "project_path": str(self.project_path),
                           "target_path": target_path
                       })
        
        try:
            # Execute the command
            result = subprocess.run(
                full_command,
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=config.timeout
            )
            
            execution_time = time.time() - start_time
            success = result.returncode == 0
            
            # Log execution result
            if MONITORING_AVAILABLE:
                log_level = LogLevel.INFO if success else LogLevel.WARN
                logger.log(log_level, LogCategory.SHELL_CMD, 
                          f"Command {'succeeded' if success else 'failed'}: {command_str}",
                          context={
                              "command_type": command_type.value,
                              "exit_code": result.returncode,
                              "execution_time_seconds": round(execution_time, 2),
                              "stdout_length": len(result.stdout),
                              "stderr_length": len(result.stderr),
                              "success": success
                          })
                
                # Log stdout/stderr if not successful or verbose logging
                if not success or logger.level <= LogLevel.DEBUG:
                    if result.stdout:
                        logger.debug(LogCategory.SHELL_CMD, f"STDOUT: {result.stdout[:500]}")
                    if result.stderr:
                        logger.debug(LogCategory.SHELL_CMD, f"STDERR: {result.stderr[:500]}")
            
            return CommandResult(
                success=success,
                command=command_str,
                args=args or [],
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                execution_time=execution_time,
                error_message=result.stderr if not success else None,
                timeout=False
            )
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            error_msg = f"Command timed out after {config.timeout} seconds"
            
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.SHELL_CMD, f"Command timeout: {command_str}",
                           context={
                               "command_type": command_type.value,
                               "timeout_seconds": config.timeout,
                               "execution_time_seconds": round(execution_time, 2)
                           })
            
            return CommandResult(
                success=False,
                command=command_str,
                args=args or [],
                exit_code=-1,
                stdout="",
                stderr="",
                execution_time=execution_time,
                error_message=error_msg,
                timeout=True
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Command execution failed: {str(e)}"
            
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.SHELL_CMD, f"Command exception: {command_str}",
                           context={
                               "command_type": command_type.value,
                               "error_type": type(e).__name__,
                               "error_message": str(e),
                               "execution_time_seconds": round(execution_time, 2)
                           })
            
            return CommandResult(
                success=False,
                command=command_str,
                args=args or [],
                exit_code=-1,
                stdout="",
                stderr="",
                execution_time=execution_time,
                error_message=error_msg,
                timeout=False
            )
    
    async def execute_flutter_pub_get(self) -> CommandResult:
        """Execute flutter pub get"""
        return await self.execute_command(CommandType.FLUTTER_PUB, ["get"])
    
    async def execute_flutter_pub_add(self, package_name: str) -> CommandResult:
        """Execute flutter pub add <package>"""
        return await self.execute_command(CommandType.FLUTTER_PUB, ["add", package_name])
    
    async def execute_dart_analyze(self, target_path: Optional[str] = None) -> CommandResult:
        """Execute dart analyze"""
        return await self.execute_command(CommandType.DART_ANALYZE, target_path=target_path)
    
    async def execute_dart_fix(self, apply: bool = True, target_path: Optional[str] = None) -> CommandResult:
        """Execute dart fix"""
        args = ["--apply"] if apply else ["--dry-run"]
        return await self.execute_command(CommandType.DART_FIX, args, target_path=target_path)
    
    async def execute_dart_format(self, fix: bool = True, target_path: Optional[str] = None) -> CommandResult:
        """Execute dart format"""
        args = ["--fix"] if fix else []
        return await self.execute_command(CommandType.DART_FORMAT, args, target_path=target_path)
    
    async def execute_build_runner_build(self) -> CommandResult:
        """Execute build runner build"""
        return await self.execute_command(CommandType.BUILD_RUNNER, ["build"])
    
    async def execute_flutter_clean(self) -> CommandResult:
        """Execute flutter clean"""
        return await self.execute_command(CommandType.FLUTTER_CLEAN)
    
    async def execute_flutter_doctor(self, verbose: bool = False) -> CommandResult:
        """Execute flutter doctor"""
        args = ["--verbose"] if verbose else []
        return await self.execute_command(CommandType.FLUTTER_DOCTOR, args)
    
    def get_command_suggestions(self, error_output: str) -> List[Tuple[CommandType, List[str]]]:
        """
        Suggest commands based on error output
        
        Args:
            error_output: Flutter/Dart error output
            
        Returns:
            List of (command_type, args) tuples to try
        """
        suggestions = []
        error_lower = error_output.lower()
        
        # Dependency issues
        if any(pattern in error_lower for pattern in [
            "target of uri doesn't exist",
            "package not found",
            "import of",
            "pub get failed",
            "dependency"
        ]):
            suggestions.append((CommandType.FLUTTER_PUB, ["get"]))
        
        # Build runner issues
        if any(pattern in error_lower for pattern in [
            "part of",
            ".g.dart",
            "build_runner",
            "generated",
            "code generation"
        ]):
            suggestions.append((CommandType.BUILD_RUNNER, ["build"]))
        
        # Formatting issues
        if any(pattern in error_lower for pattern in [
            "formatting",
            "expected ';'",
            "unexpected token",
            "syntax error"
        ]):
            suggestions.append((CommandType.DART_FORMAT, ["--fix"]))
        
        # Auto-fixable issues
        if any(pattern in error_lower for pattern in [
            "unused import",
            "dead code",
            "unnecessary",
            "prefer_const"
        ]):
            suggestions.append((CommandType.DART_FIX, ["--apply"]))
        
        # Build cache issues
        if any(pattern in error_lower for pattern in [
            "build failed",
            "cache",
            "corrupted",
            "clean"
        ]):
            suggestions.append((CommandType.FLUTTER_CLEAN, []))
        
        return suggestions
    
    def format_command_result(self, result: CommandResult) -> str:
        """Format command result for logging/display"""
        status = "✅" if result.success else "❌"
        duration = f"{result.execution_time:.1f}s"
        
        output = f"{status} {result.command} ({duration})"
        
        if not result.success:
            if result.timeout:
                output += f" - TIMEOUT after {result.execution_time:.1f}s"
            elif result.error_message:
                output += f" - {result.error_message}"
            else:
                output += f" - Exit code: {result.exit_code}"
        
        return output


# Global instance for easy access
_command_executor = None

def get_command_executor(project_path: str) -> CommandExecutor:
    """Get or create the global command executor instance"""
    global _command_executor
    if _command_executor is None or str(_command_executor.project_path) != project_path:
        _command_executor = CommandExecutor(project_path)
    return _command_executor