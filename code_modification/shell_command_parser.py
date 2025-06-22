"""
Shell Command Parser
Parses and executes shell commands from AI responses with <shell> tags
"""

import subprocess
import re
import time
import asyncio
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

# Import advanced logging and monitoring
try:
    from utils.advanced_logger import logger, LogCategory, LogLevel
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False


@dataclass
class ShellCommand:
    """Represents a shell command found in AI response"""
    command: str
    description: Optional[str] = None
    raw_text: str = ""
    line_number: int = 0


@dataclass
class CommandExecution:
    """Result of executing a shell command"""
    command: str
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    error_message: Optional[str] = None


class ShellCommandParser:
    """
    Parses <shell> tags from AI responses and executes commands safely
    """
    
    def __init__(self, project_path: str, enable_execution: bool = True):
        self.project_path = Path(project_path)
        self.enable_execution = enable_execution
        
        # Whitelist of allowed command prefixes for security
        self.allowed_commands = [
            "flutter",
            "dart", 
            "npm",
            "yarn",
            "git",
            "ls",
            "pwd",
            "echo",
            "cat",
            "grep",
            "find"
        ]
        
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.SYSTEM, "ShellCommandParser initialized",
                       context={
                           "project_path": str(self.project_path),
                           "execution_enabled": self.enable_execution,
                           "allowed_commands": len(self.allowed_commands)
                       })
    
    def parse_shell_commands(self, ai_response: str) -> List[ShellCommand]:
        """
        Parse <shell> tags from AI response text
        
        Args:
            ai_response: The full AI response text
            
        Returns:
            List of ShellCommand objects found in the response
        """
        commands = []
        
        # Pattern to match <shell>command</shell> or <shell description="...">command</shell>
        shell_pattern = r'<shell(?:\s+description="([^"]*)")?\s*>(.*?)</shell>'
        
        matches = re.finditer(shell_pattern, ai_response, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            description = match.group(1)  # Optional description attribute
            command_text = match.group(2).strip()  # Command content
            
            # Skip empty commands
            if not command_text:
                continue
            
            # Handle multi-line commands (take the first significant line)
            command_lines = [line.strip() for line in command_text.split('\n') if line.strip()]
            if not command_lines:
                continue
            
            # Use the first non-comment line as the command
            command = None
            for line in command_lines:
                if not line.startswith('#') and not line.startswith('//'):
                    command = line
                    break
            
            if command:
                commands.append(ShellCommand(
                    command=command,
                    description=description,
                    raw_text=command_text,
                    line_number=ai_response[:match.start()].count('\n') + 1
                ))
        
        if MONITORING_AVAILABLE and commands:
            logger.info(LogCategory.SYSTEM, f"Parsed {len(commands)} shell commands from AI response",
                       context={
                           "commands": [cmd.command for cmd in commands],
                           "descriptions": [cmd.description for cmd in commands if cmd.description]
                       })
        
        return commands
    
    def is_command_safe(self, command: str) -> Tuple[bool, str]:
        """
        Check if a command is safe to execute
        
        Args:
            command: The command to check
            
        Returns:
            (is_safe, reason) tuple
        """
        # Basic safety checks
        if not command or not command.strip():
            return False, "Empty command"
        
        # Check for dangerous patterns
        dangerous_patterns = [
            "rm -rf",
            "sudo",
            "chmod 777",
            "wget",
            "curl -L",
            "eval",
            "exec",
            ">",  # Output redirection could be dangerous
            "|",  # Pipes could be chained maliciously
            "&&", # Command chaining
            "||", # Command chaining
            ";",  # Command separation
            "`",  # Command substitution
            "$(",  # Command substitution
        ]
        
        command_lower = command.lower()
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                return False, f"Contains dangerous pattern: {pattern}"
        
        # Check if command starts with allowed prefix
        command_parts = command.strip().split()
        if not command_parts:
            return False, "No command found"
        
        base_command = command_parts[0].lower()
        
        # Allow exact matches or subcommands (e.g., "flutter pub get")
        is_allowed = any(
            base_command == allowed or base_command.startswith(allowed + " ")
            for allowed in self.allowed_commands
        )
        
        if not is_allowed:
            return False, f"Command '{base_command}' not in allowed list"
        
        return True, "Command is safe"
    
    async def execute_command(self, shell_command: ShellCommand) -> CommandExecution:
        """
        Execute a single shell command safely
        
        Args:
            shell_command: The ShellCommand to execute
            
        Returns:
            CommandExecution with results
        """
        command = shell_command.command
        start_time = time.time()
        
        # Safety check
        is_safe, safety_reason = self.is_command_safe(command)
        if not is_safe:
            error_msg = f"Command blocked for safety: {safety_reason}"
            if MONITORING_AVAILABLE:
                logger.warn(LogCategory.SYSTEM, error_msg,
                           context={"command": command, "reason": safety_reason})
            
            return CommandExecution(
                command=command,
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                execution_time=time.time() - start_time,
                error_message=error_msg
            )
        
        # Check if execution is enabled
        if not self.enable_execution:
            if MONITORING_AVAILABLE:
                logger.info(LogCategory.SYSTEM, f"Command execution disabled, would run: {command}")
            
            return CommandExecution(
                command=command,
                success=True,
                exit_code=0,
                stdout="Command execution disabled (dry run mode)",
                stderr="",
                execution_time=time.time() - start_time,
                error_message=None
            )
        
        # Execute the command
        if MONITORING_AVAILABLE:
            logger.info(LogCategory.SYSTEM, f"Executing shell command: {command}",
                       context={
                           "description": shell_command.description,
                           "project_path": str(self.project_path)
                       })
        
        try:
            # Split command properly for subprocess
            if isinstance(command, str):
                command_parts = command.split()
            else:
                command_parts = command
            
            result = subprocess.run(
                command_parts,
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            execution_time = time.time() - start_time
            success = result.returncode == 0
            
            if MONITORING_AVAILABLE:
                status = "succeeded" if success else "failed"
                logger.info(LogCategory.SYSTEM, f"Command {status}: {command}",
                           context={
                               "exit_code": result.returncode,
                               "execution_time_seconds": round(execution_time, 2),
                               "stdout_length": len(result.stdout),
                               "stderr_length": len(result.stderr)
                           })
            
            return CommandExecution(
                command=command,
                success=success,
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                execution_time=execution_time,
                error_message=result.stderr if not success else None
            )
            
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            error_msg = f"Command timed out after 2 minutes"
            
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.SYSTEM, f"Command timeout: {command}",
                           context={"timeout_seconds": 120})
            
            return CommandExecution(
                command=command,
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                execution_time=execution_time,
                error_message=error_msg
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Command execution failed: {str(e)}"
            
            if MONITORING_AVAILABLE:
                logger.error(LogCategory.SYSTEM, f"Command exception: {command}",
                           context={"error": str(e)})
            
            return CommandExecution(
                command=command,
                success=False,
                exit_code=-1,
                stdout="",
                stderr="",
                execution_time=execution_time,
                error_message=error_msg
            )
    
    async def execute_all_commands(self, shell_commands: List[ShellCommand]) -> List[CommandExecution]:
        """
        Execute all shell commands in sequence
        
        Args:
            shell_commands: List of ShellCommand objects to execute
            
        Returns:
            List of CommandExecution results
        """
        results = []
        
        for shell_command in shell_commands:
            result = await self.execute_command(shell_command)
            results.append(result)
            
            # Small delay between commands
            await asyncio.sleep(0.5)
        
        return results
    
    async def parse_and_execute(self, ai_response: str) -> Tuple[List[ShellCommand], List[CommandExecution]]:
        """
        Parse shell commands from AI response and execute them
        
        Args:
            ai_response: The AI response text containing <shell> tags
            
        Returns:
            (parsed_commands, execution_results) tuple
        """
        # Parse commands
        shell_commands = self.parse_shell_commands(ai_response)
        
        if not shell_commands:
            return [], []
        
        # Execute commands
        executions = await self.execute_all_commands(shell_commands)
        
        return shell_commands, executions
    
    def format_execution_summary(self, executions: List[CommandExecution]) -> str:
        """Format a summary of command executions"""
        if not executions:
            return "No commands executed"
        
        summary_parts = []
        successful = sum(1 for exec in executions if exec.success)
        failed = len(executions) - successful
        
        summary_parts.append(f"Commands: {successful}✅ {failed}❌")
        
        for execution in executions:
            status = "✅" if execution.success else "❌"
            duration = f"{execution.execution_time:.1f}s"
            summary_parts.append(f"{status} {execution.command} ({duration})")
            
            if not execution.success and execution.error_message:
                summary_parts.append(f"   Error: {execution.error_message}")
        
        return "\n".join(summary_parts)


# Global instance
_shell_parser = None

def get_shell_command_parser(project_path: str, enable_execution: bool = True) -> ShellCommandParser:
    """Get or create the global shell command parser"""
    global _shell_parser
    if (_shell_parser is None or 
        str(_shell_parser.project_path) != project_path or 
        _shell_parser.enable_execution != enable_execution):
        _shell_parser = ShellCommandParser(project_path, enable_execution)
    return _shell_parser