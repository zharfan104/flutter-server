# Test Prompts for Error Recovery System

Use these prompts with the AI assistant to introduce compilation errors across multiple files for testing the enhanced recovery system.

## Prompt 1: Import and Dependency Errors

```
Break the Flutter project with import and dependency errors across multiple files:

1. In lib/main.dart: Remove the import for 'package:flutter/material.dart' 
2. In lib/models/product.dart: Add import for a non-existent package 'package:fake_package/fake.dart'
3. In lib/services/api_service.dart: Change http import to 'package:http_wrong/http.dart'
4. In lib/screens/home_screen.dart: Remove the import for the ProductModel
5. In pubspec.yaml: Comment out the http dependency

This will create multiple import errors that should trigger flutter pub get and package additions.
```

## Prompt 2: Type and Syntax Errors

```
Introduce type and syntax errors in multiple files:

1. In lib/models/user.dart: Remove type annotations from 3 properties (make them dynamic)
2. In lib/widgets/user_card.dart: Change Widget return type to int in build method
3. In lib/services/auth_service.dart: Add a method that returns Future<String> but return an int
4. In lib/utils/validators.dart: Remove semicolons from 2-3 lines
5. In lib/constants/app_constants.dart: Add unclosed parentheses in a const declaration

This will create syntax and type errors that dart format and targeted fixes should resolve.
```

## Prompt 3: Generated Code and Build Runner Issues

```
Break generated code and build runner functionality:

1. Delete all .g.dart files from lib/models/ 
2. In lib/models/product.dart: Add @JsonSerializable() annotation but remove the generated import
3. In lib/models/user.dart: Add part 'user.g.dart'; but delete the actual user.g.dart file
4. In lib/api/api_client.dart: Reference ProductModel.fromJson() method that won't exist without generated code
5. In pubspec.yaml: Comment out the json_annotation and build_runner dependencies

This will create generated code errors that should trigger build_runner build commands.
```

## Prompt 4: Mixed Complex Errors

```
Create a complex mix of errors across the entire project:

1. Remove flutter/material.dart import from 3 different screen files
2. Delete 2 .g.dart files and add references to their missing methods
3. Add syntax errors (missing semicolons, unclosed brackets) in 4 files
4. Change method return types to incompatible types in 2 service files  
5. Add imports for non-existent packages in 3 different files
6. Comment out 2 dependencies in pubspec.yaml that are used in the code
7. Add @JsonSerializable annotations without proper imports
8. Remove part declarations for generated files that are referenced

This creates a comprehensive test with ~20+ errors across imports, types, generated code, and dependencies.
```

## Prompt 5: Gradual Error Introduction

```
Introduce errors one category at a time to test iterative recovery:

Step 1: "Add import errors in lib/main.dart and lib/screens/home_screen.dart - remove flutter/material imports"

Step 2: "Now add type errors - change the return type of build() method in 2 widget files from Widget to String"  

Step 3: "Add generated code issues - delete lib/models/product.g.dart but keep references to Product.fromJson()"

Step 4: "Finally add dependency issues - comment out http and json_annotation in pubspec.yaml"

Use each step separately to test how the system handles progressive error introduction.
```

## Prompt 6: Specific Test Cases

### Test Case A: Pure Import Errors
```
Create only import and dependency errors:
- Remove flutter/material imports from 5 files
- Add imports for 'package:fake_one/fake.dart' and 'package:fake_two/fake.dart' 
- Comment out http, provider, and json_annotation from pubspec.yaml
- Keep all other code syntactically correct

Expected: System should run flutter pub get and attempt to add missing packages
```

### Test Case B: Pure Syntax Errors  
```
Create only syntax and formatting errors:
- Remove semicolons from 6 different lines across 3 files
- Add unclosed parentheses in 2 const declarations
- Add extra commas in widget constructors
- Keep all imports and types correct

Expected: System should run dart format and apply targeted syntax fixes
```

### Test Case C: Pure Generated Code Errors
```
Create only generated code issues:
- Delete all .g.dart files in lib/models/
- Ensure all models have @JsonSerializable() and part declarations
- Keep references to .fromJson() and .toJson() methods in API code
- Keep all dependencies in pubspec.yaml

Expected: System should run flutter packages pub run build_runner build
```

## Usage Instructions

### For Manual Testing:
1. Start with a clean, working Flutter project
2. Use one of the prompts above with the AI assistant
3. Let the AI introduce the errors as specified
4. Trigger hot reload to see compilation errors
5. Watch the enhanced recovery system work

### For Automated Testing:
```bash
# Run the test script after introducing errors
python test_recovery_system.py

# Or test the recovery service directly
curl -X POST http://localhost:5000/api/hot-reload
```

### Expected Recovery Process:
1. **Error Detection**: System detects compilation failures
2. **Analysis**: Dart analyze runs to identify all errors
3. **Command Execution**: Appropriate commands run automatically:
   - `flutter pub get` for import errors
   - `build_runner build` for generated code
   - `dart format .` for syntax issues
   - `dart fix --apply` for linting issues
4. **AI Fixes**: Targeted code fixes applied for remaining errors
5. **Validation**: Process repeats until clean or max attempts
6. **Success**: Hot reload works again

### What to Look For:
- ✅ Commands executed automatically based on error types
- ✅ Progress messages showing step-by-step recovery
- ✅ Error count reduction with each attempt  
- ✅ Detailed logging of all actions taken
- ✅ Final success with working hot reload

### Example Success Output:
```
🔧 Starting Comprehensive Error Recovery
🔍 Running Comprehensive Dart Analysis - Found 23 errors
✅ flutter pub get (8.3s) - Resolved 12 import errors  
✅ build_runner build (15.2s) - Generated 3 .g.dart files
🔧 Applying 8 targeted code fixes
✅ dart format . (2.1s) - Fixed syntax errors
✅ Error Recovery Successful! (28.7s)
   • Errors: 23 → 0
   • Commands: 3  
   • Fixes: 8
```

## Pro Tips for Testing

1. **Start Simple**: Begin with Prompt 1 or Test Case A to verify basic functionality
2. **Progressive Testing**: Use Prompt 5 to test how the system handles evolving errors
3. **Complex Scenarios**: Use Prompt 4 for comprehensive stress testing
4. **Monitor Logs**: Check the generated log files for detailed analysis
5. **Verify Commands**: Ensure the right commands are executed for each error type

The system should handle all these scenarios automatically and provide detailed feedback on its recovery process!