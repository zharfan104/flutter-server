# Flutter AI Code Modification Prompts

This directory contains specialized YAML prompt files for different types of AI-powered code modifications in Flutter projects. Each prompt is designed for specific tasks and follows a consistent structure.

## Available Prompts

### Core Modification Prompts

| Prompt | Description | Use Case |
|--------|-------------|----------|
| **determine_files.yaml** | Determines which files need to be modified, created, or deleted | Initial analysis phase of any code modification request |
| **generate_code.yaml** | Generates complete, production-ready code modifications | Main code generation for features, bug fixes, and enhancements |

### Specialized Task Prompts

| Prompt | Description | Use Case |
|--------|-------------|----------|
| **refactoring.yaml** | Code refactoring and optimization tasks | Improving code structure, extracting widgets/methods, renaming |
| **testing.yaml** | Generates comprehensive test cases | Creating unit tests, widget tests, and integration tests |
| **validation.yaml** | Validates generated code before applying modifications | Quality assurance and error prevention |
| **error_analysis.yaml** | Analyzes compilation and runtime errors to suggest fixes | Debugging and error resolution |

### Advanced Analysis Prompts

| Prompt | Description | Use Case |
|--------|-------------|----------|
| **architecture_analysis.yaml** | Analyzes and improves Flutter application architecture | Architecture reviews, technical debt assessment |
| **performance_optimization.yaml** | Analyzes and optimizes Flutter application performance | Performance tuning, memory optimization, rendering improvements |
| **dependency_management.yaml** | Manages Flutter project dependencies and packages | Package updates, dependency optimization, security audits |

## Prompt Structure

Each YAML prompt file follows this structure:

```yaml
name: "prompt_name"
description: "Brief description of the prompt's purpose"
version: "1.0"
template: |
  # Detailed prompt template with placeholders
  # Uses {variable_name} syntax for parameter substitution
```

## Usage in Code

```python
from code_modification.prompt_loader import prompt_loader

# Get formatted prompt
prompt = prompt_loader.format_prompt(
    'determine_files',
    project_summary=project_data,
    change_request=user_request
)

# Get prompt metadata
info = prompt_loader.get_prompt_info('generate_code')
print(f"Description: {info['description']}")
print(f"Version: {info['version']}")
```

## Parameter Conventions

### Common Parameters

- **project_summary**: JSON string containing project structure and metadata
- **change_request**: User's description of the desired modification
- **current_contents**: Current file contents for modification
- **target_files**: List of files to be modified

### Specialized Parameters

- **error_details**: Error messages and stack traces (error_analysis)
- **performance_metrics**: Performance measurements (performance_optimization)
- **refactoring_request**: Specific refactoring requirements (refactoring)
- **current_pubspec**: Current pubspec.yaml contents (dependency_management)

## Response Formats

### File Modifications
```xml
<files path="lib/example.dart">
// Generated Dart code here
</files>
```

### File Deletions
```xml
<delete path="lib/old_file.dart">DELETE</delete>
```

### Shell Commands
```xml
<shell>
flutter pub get
dart format .
</shell>
```

### JSON Responses
```json
{
  "analysis_result": "structured data",
  "recommendations": ["list", "of", "suggestions"]
}
```

## Best Practices

### Prompt Design
- Use clear, specific instructions
- Include comprehensive examples
- Specify exact output formats
- Emphasize Flutter/Dart best practices
- Include error handling guidelines

### Parameter Substitution
- Use descriptive parameter names
- Provide fallback values where appropriate
- Validate parameter types in code
- Document required vs optional parameters

### Response Parsing
- Use consistent XML/JSON formats
- Include validation patterns
- Handle partial responses gracefully
- Provide clear error messages

## Extending the System

To add a new prompt:

1. Create a new YAML file in this directory
2. Follow the standard structure (name, description, version, template)
3. Add parameter documentation to this README
4. Test with the prompt_loader
5. Update any code that needs to use the new prompt

Example minimal prompt:

```yaml
name: "new_feature"
description: "Generates new feature scaffolding"
version: "1.0"
template: |
  Generate a new Flutter feature for: {feature_description}
  
  Project structure: {project_summary}
  
  Create the following files:
  <files path="lib/features/{feature_name}/feature.dart">
  // Generated feature code
  </files>
```

## Maintenance

- Regularly review and update prompts based on feedback
- Version prompts when making significant changes
- Test prompts with various project structures
- Keep examples current with latest Flutter practices
- Monitor AI model performance with different prompts