"""
Tests for SimpleDartAnalysisFixer

Unit tests for the simple dart analysis fixer system.
"""

import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from src.code_modification.services.simple_dart_fixer import (
    SimpleDartAnalysisFixer,
    FileQueue,
    FileQueueItem,
    FixResult,
    AnalysisError,
    AnalysisResult
)


class TestFileQueueItem:
    """Tests for FileQueueItem dataclass"""
    
    def test_file_queue_item_creation(self):
        """Test FileQueueItem can be created with required fields"""
        item = FileQueueItem(
            path="lib/main.dart",
            operation="modify",
            reason="Fix undefined method error"
        )
        
        assert item.path == "lib/main.dart"
        assert item.operation == "modify"
        assert item.reason == "Fix undefined method error"
        assert item.priority == 1  # default value
        assert item.completed == False  # default value
    
    def test_file_queue_item_with_custom_values(self):
        """Test FileQueueItem with custom priority and completion status"""
        item = FileQueueItem(
            path="lib/widgets/button.dart",
            operation="create",
            reason="Add missing widget",
            priority=2,
            completed=True
        )
        
        assert item.priority == 2
        assert item.completed == True


class TestFileQueue:
    """Tests for FileQueue class"""
    
    def test_file_queue_initialization(self):
        """Test FileQueue initializes empty"""
        queue = FileQueue()
        assert len(queue.items) == 0
        assert queue.is_empty() == True
        assert queue.get_pending_count() == 0
    
    def test_add_file_to_queue(self):
        """Test adding files to the queue"""
        queue = FileQueue()
        
        queue.add_file("lib/main.dart", "modify", "Fix error")
        queue.add_file("lib/new.dart", "create", "Add widget", priority=2)
        
        assert len(queue.items) == 2
        assert queue.get_pending_count() == 2
        assert queue.is_empty() == False
        
        # Check first item
        assert queue.items[0].path == "lib/main.dart"
        assert queue.items[0].operation == "modify"
        assert queue.items[0].reason == "Fix error"
        assert queue.items[0].priority == 1
        assert queue.items[0].completed == False
        
        # Check second item
        assert queue.items[1].priority == 2
    
    def test_get_next_file(self):
        """Test getting next uncompleted file from queue"""
        queue = FileQueue()
        
        # Empty queue
        assert queue.get_next() is None
        
        # Add files
        queue.add_file("lib/first.dart", "modify", "Fix first")
        queue.add_file("lib/second.dart", "create", "Create second")
        
        # Get next should return first uncompleted
        next_item = queue.get_next()
        assert next_item is not None
        assert next_item.path == "lib/first.dart"
        
        # Mark first as completed
        queue.mark_completed(next_item)
        
        # Get next should return second file
        next_item = queue.get_next()
        assert next_item.path == "lib/second.dart"
    
    def test_mark_completed(self):
        """Test marking files as completed"""
        queue = FileQueue()
        queue.add_file("lib/test.dart", "modify", "Fix test")
        
        item = queue.get_next()
        assert item.completed == False
        assert queue.get_pending_count() == 1
        
        queue.mark_completed(item)
        assert item.completed == True
        assert queue.get_pending_count() == 0
        assert queue.is_empty() == True
    
    def test_queue_empty_state(self):
        """Test queue empty detection"""
        queue = FileQueue()
        
        # Empty queue
        assert queue.is_empty() == True
        
        # Add and complete all files
        queue.add_file("lib/test.dart", "modify", "Fix test")
        assert queue.is_empty() == False
        
        item = queue.get_next()
        queue.mark_completed(item)
        assert queue.is_empty() == True
    
    def test_clear_queue(self):
        """Test clearing the queue"""
        queue = FileQueue()
        queue.add_file("lib/test1.dart", "modify", "Fix test1")
        queue.add_file("lib/test2.dart", "create", "Create test2")
        
        assert len(queue.items) == 2
        
        queue.clear()
        assert len(queue.items) == 0
        assert queue.is_empty() == True


class TestSimpleDartAnalysisFixer:
    """Tests for SimpleDartAnalysisFixer class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir)
        
        # Create a minimal pubspec.yaml to make it a valid Dart project
        pubspec_content = """
name: test_project
description: A test Flutter project

version: 1.0.0+1

environment:
  sdk: '>=3.0.0 <4.0.0'
  flutter: ">=3.0.0"

dependencies:
  flutter:
    sdk: flutter

dev_dependencies:
  flutter_test:
    sdk: flutter

flutter:
  uses-material-design: true
"""
        pubspec_path = self.project_path / "pubspec.yaml"
        pubspec_path.write_text(pubspec_content.strip())
        
        # Create lib directory
        lib_dir = self.project_path / "lib"
        lib_dir.mkdir(exist_ok=True)
    
    def teardown_method(self):
        """Clean up test fixtures"""
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialization_valid_project(self):
        """Test SimpleDartAnalysisFixer initialization with valid project"""
        fixer = SimpleDartAnalysisFixer(str(self.project_path), max_attempts=3)
        
        assert fixer.project_path == self.project_path
        assert fixer.max_attempts == 3
        assert fixer.current_attempt == 0
        assert isinstance(fixer.file_queue, FileQueue)
        assert isinstance(fixer.memory_entries, list)
        assert len(fixer.memory_entries) == 0
        assert fixer.session_id.startswith("dart_fix_")
    
    def test_initialization_default_max_attempts(self):
        """Test SimpleDartAnalysisFixer with default max_attempts"""
        fixer = SimpleDartAnalysisFixer(str(self.project_path))
        assert fixer.max_attempts == 5  # default value
    
    def test_initialization_invalid_project_path(self):
        """Test SimpleDartAnalysisFixer with non-existent path"""
        try:
            SimpleDartAnalysisFixer("/non/existent/path")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Project path does not exist" in str(e)
    
    def test_initialization_not_dart_project(self):
        """Test SimpleDartAnalysisFixer with directory without pubspec.yaml"""
        # Create temp directory without pubspec.yaml
        no_pubspec_dir = tempfile.mkdtemp()
        try:
            SimpleDartAnalysisFixer(no_pubspec_dir)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Not a valid Dart/Flutter project" in str(e)
        finally:
            shutil.rmtree(no_pubspec_dir, ignore_errors=True)
    
    def test_repr(self):
        """Test string representation of SimpleDartAnalysisFixer"""
        fixer = SimpleDartAnalysisFixer(str(self.project_path), max_attempts=3)
        repr_str = repr(fixer)
        
        assert "SimpleDartAnalysisFixer" in repr_str
        assert str(self.project_path) in repr_str
        assert "max_attempts=3" in repr_str
    
    def test_file_queue_integration(self):
        """Test that the fixer has a working file queue"""
        fixer = SimpleDartAnalysisFixer(str(self.project_path))
        
        # Initially empty
        assert fixer.file_queue.is_empty() == True
        
        # Can add files to queue
        fixer.file_queue.add_file("lib/test.dart", "modify", "Fix test")
        assert fixer.file_queue.is_empty() == False
        assert fixer.file_queue.get_pending_count() == 1


class TestFixResult:
    """Tests for FixResult dataclass"""
    
    def test_fix_result_creation(self):
        """Test FixResult can be created with required fields"""
        result = FixResult(
            success=True,
            initial_error_count=5,
            final_error_count=0,
            attempts_made=2,
            files_processed=["lib/main.dart", "lib/widget.dart"],
            total_duration=45.5
        )
        
        assert result.success == True
        assert result.initial_error_count == 5
        assert result.final_error_count == 0
        assert result.attempts_made == 2
        assert result.files_processed == ["lib/main.dart", "lib/widget.dart"]
        assert result.total_duration == 45.5
        assert result.error_message is None  # default value
    
    def test_fix_result_with_error(self):
        """Test FixResult with error message"""
        result = FixResult(
            success=False,
            initial_error_count=3,
            final_error_count=3,
            attempts_made=5,
            files_processed=[],
            total_duration=120.0,
            error_message="Max attempts reached"
        )
        
        assert result.success == False
        assert result.error_message == "Max attempts reached"


class TestAnalysisError:
    """Tests for AnalysisError dataclass"""
    
    def test_analysis_error_creation(self):
        """Test AnalysisError can be created with required fields"""
        error = AnalysisError(
            file_path="lib/main.dart",
            line=25,
            column=5,
            message="The method 'foo' isn't defined"
        )
        
        assert error.file_path == "lib/main.dart"
        assert error.line == 25
        assert error.column == 5
        assert error.message == "The method 'foo' isn't defined"
        assert error.error_type == "error"  # default value
    
    def test_analysis_error_with_custom_type(self):
        """Test AnalysisError with custom error type"""
        warning = AnalysisError(
            file_path="lib/widgets.dart",
            line=10,
            column=1,
            message="Unused import",
            error_type="warning"
        )
        
        assert warning.error_type == "warning"


class TestAnalysisResult:
    """Tests for AnalysisResult dataclass"""
    
    def test_analysis_result_creation(self):
        """Test AnalysisResult can be created"""
        errors = [AnalysisError("lib/main.dart", 25, 5, "Undefined method")]
        warnings = [AnalysisError("lib/main.dart", 3, 8, "Unused import", "warning")]
        
        result = AnalysisResult(
            success=False,
            errors=errors,
            warnings=warnings,
            output="dart analyze output...",
            execution_time=2.5
        )
        
        assert result.success == False
        assert len(result.errors) == 1
        assert len(result.warnings) == 1
        assert result.output == "dart analyze output..."
        assert result.execution_time == 2.5
        assert result.errors[0].message == "Undefined method"
        assert result.warnings[0].error_type == "warning"


class TestDartAnalysisRunner:
    """Tests for dart analysis functionality in SimpleDartAnalysisFixer"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir)
        
        # Create a minimal pubspec.yaml to make it a valid Dart project
        pubspec_content = """
name: test_project
description: A test Flutter project

version: 1.0.0+1

environment:
  sdk: '>=3.0.0 <4.0.0'
  flutter: ">=3.0.0"

dependencies:
  flutter:
    sdk: flutter

dev_dependencies:
  flutter_test:
    sdk: flutter

flutter:
  uses-material-design: true
"""
        pubspec_path = self.project_path / "pubspec.yaml"
        pubspec_path.write_text(pubspec_content.strip())
        
        # Create lib directory
        lib_dir = self.project_path / "lib"
        lib_dir.mkdir(exist_ok=True)
        
        # Create a simple main.dart file
        main_dart_content = """
import 'package:flutter/material.dart';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Test App',
      home: Scaffold(
        appBar: AppBar(title: Text('Test')),
        body: Center(child: Text('Hello World')),
      ),
    );
  }
}
"""
        main_dart_path = lib_dir / "main.dart"
        main_dart_path.write_text(main_dart_content.strip())
        
        self.fixer = SimpleDartAnalysisFixer(str(self.project_path))
    
    def teardown_method(self):
        """Clean up test fixtures"""
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_parse_dart_analysis_output_with_errors(self):
        """Test parsing dart analyze output with errors"""
        sample_output = """
error • The method 'foo' isn't defined for the type 'MyApp' • lib/main.dart:25:5 • undefined_method
warning • Unused import: 'package:flutter/services.dart' • lib/main.dart:3:8 • unused_import
info • The declaration 'bar' isn't referenced • lib/utils.dart:10:5 • unused_element
"""
        
        errors, warnings = self.fixer._parse_dart_analysis_output(sample_output)
        
        # Check errors
        assert len(errors) == 1
        error = errors[0]
        assert error.file_path == "lib/main.dart"
        assert error.line == 25
        assert error.column == 5
        assert "foo" in error.message
        assert error.error_type == "error"
        
        # Check warnings (includes warning, info, hint)
        assert len(warnings) == 2
        warning = warnings[0]
        assert warning.file_path == "lib/main.dart"
        assert warning.line == 3
        assert warning.column == 8
        assert "Unused import" in warning.message
        assert warning.error_type == "warning"
        
        info = warnings[1]
        assert info.error_type == "info"
    
    def test_parse_dart_analysis_output_clean(self):
        """Test parsing dart analyze output with no issues"""
        sample_output = "No issues found!"
        
        errors, warnings = self.fixer._parse_dart_analysis_output(sample_output)
        
        assert len(errors) == 0
        assert len(warnings) == 0
    
    def test_parse_dart_analysis_output_fallback_format(self):
        """Test parsing dart analyze output with fallback format"""
        sample_output = """
error - Some undefined method error
warning - Some unused import warning
"""
        
        errors, warnings = self.fixer._parse_dart_analysis_output(sample_output)
        
        assert len(errors) == 1
        assert errors[0].message == "Some undefined method error"
        assert errors[0].file_path == "unknown"  # fallback value
        
        assert len(warnings) == 1
        assert warnings[0].message == "Some unused import warning"
    
    @patch('subprocess.run')
    def test_run_dart_analysis_success(self, mock_subprocess):
        """Test successful dart analyze run"""
        # Mock successful subprocess result
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "No issues found!"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        result = self.fixer._run_dart_analysis()
        
        assert result.success == True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0
        assert result.output == "No issues found!"
        assert result.execution_time > 0
        
        # Verify subprocess was called correctly
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args
        assert call_args[0][0] == ["dart", "analyze", "lib"]
        assert call_args[1]["cwd"] == str(self.project_path)
    
    @patch('subprocess.run')
    def test_run_dart_analysis_with_errors(self, mock_subprocess):
        """Test dart analyze run with errors"""
        # Mock subprocess result with errors
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = "error • The method 'foo' isn't defined • lib/main.dart:25:5 • undefined_method"
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        result = self.fixer._run_dart_analysis()
        
        assert result.success == False
        assert len(result.errors) == 1
        assert result.errors[0].message == "The method 'foo' isn't defined"
        assert result.errors[0].file_path == "lib/main.dart"
    
    @patch('subprocess.run')
    def test_run_dart_analysis_timeout(self, mock_subprocess):
        """Test dart analyze timeout"""
        from subprocess import TimeoutExpired
        mock_subprocess.side_effect = TimeoutExpired("dart", 60)
        
        result = self.fixer._run_dart_analysis()
        
        assert result.success == False
        assert len(result.errors) == 1
        assert "timed out" in result.errors[0].message
        assert result.execution_time == 60.0
    
    @patch('subprocess.run')
    def test_run_dart_analysis_exception(self, mock_subprocess):
        """Test dart analyze with general exception"""
        mock_subprocess.side_effect = Exception("Command not found")
        
        result = self.fixer._run_dart_analysis()
        
        assert result.success == False
        assert len(result.errors) == 1
        assert "Failed to run dart analyze" in result.errors[0].message
        assert "Command not found" in result.errors[0].message
    
    def test_run_dart_analysis_invalid_target_path(self):
        """Test dart analyze with non-existent target path"""
        result = self.fixer._run_dart_analysis("non_existent_dir")
        
        assert result.success == False
        assert len(result.errors) == 1
        assert "Target path does not exist" in result.errors[0].message


class TestErrorContextCollection:
    """Tests for error context collection functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create temporary directory for testing
        self.temp_dir = tempfile.mkdtemp()
        self.project_path = Path(self.temp_dir)
        
        # Create a minimal pubspec.yaml
        pubspec_content = """
name: test_project
description: A test Flutter project

version: 1.0.0+1

environment:
  sdk: '>=3.0.0 <4.0.0'
  flutter: ">=3.0.0"

dependencies:
  flutter:
    sdk: flutter
  http: ^0.13.0
  provider: ^6.0.0

dev_dependencies:
  flutter_test:
    sdk: flutter

flutter:
  uses-material-design: true
"""
        pubspec_path = self.project_path / "pubspec.yaml"
        pubspec_path.write_text(pubspec_content.strip())
        
        # Create lib directory
        lib_dir = self.project_path / "lib"
        lib_dir.mkdir(exist_ok=True)
        
        # Create a Dart file with intentional errors
        dart_content = """
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Test App',
      home: HomePage(),
    );
  }
}

class HomePage extends StatefulWidget {
  @override
  _HomePageState createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  void fetchData() async {
    // This line has an error - undefined method
    var response = await http.undefinedMethod();
    print(response);
  }
  
  void anotherMethod() {
    // Another error line
    nonExistentFunction();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Home')),
      body: Center(
        child: ElevatedButton(
          onPressed: fetchData,
          child: Text('Fetch Data'),
        ),
      ),
    );
  }
}
"""
        main_dart_path = lib_dir / "main.dart"
        main_dart_path.write_text(dart_content.strip())
        
        self.fixer = SimpleDartAnalysisFixer(str(self.project_path))
    
    def teardown_method(self):
        """Clean up test fixtures"""
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_extract_dart_structure(self):
        """Test extracting Dart structure from file content"""
        dart_content = """
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(title: 'Test');
  }
  
  void myMethod() {
    print('test');
  }
}

void globalFunction() {
  // global function
}
"""
        
        structure = {
            "imports": set(),
            "classes": set(),
            "methods": set(),
            "dependencies": []
        }
        
        self.fixer._extract_dart_structure(dart_content, structure)
        
        # Check imports
        assert "package:flutter/material.dart" in structure["imports"]
        assert "package:http/http.dart" in structure["imports"]
        
        # Check classes
        assert "MyApp" in structure["classes"]
        
        # Check methods (this is basic extraction, may catch some false positives)
        assert "build" in structure["methods"] or "myMethod" in structure["methods"]
    
    def test_get_error_line_context(self):
        """Test getting context around an error line"""
        content = """Line 1
Line 2
Line 3
void myFunction() {
  var x = undefinedMethod();  // Error on this line
  print(x);
}
Line 8
Line 9
Line 10"""
        
        context = self.fixer._get_error_line_context(content, 5, 10)  # Line 5, column 10
        
        assert context["target_line"] == "  var x = undefinedMethod();  // Error on this line"
        assert len(context["surrounding_lines"]) > 0
        # The target line should be marked with ">>> " somewhere in the surrounding lines
        target_line_found = any(">>> " in line for line in context["surrounding_lines"])
        assert target_line_found, f"Target line not found in: {context['surrounding_lines']}"
        assert "myFunction" in context["function_context"]
    
    def test_find_containing_function(self):
        """Test finding the function that contains a target line"""
        lines = [
            "import 'package:flutter/material.dart';",
            "",
            "class MyClass {",
            "  void myMethod() {",
            "    var x = 1;",
            "    undefinedMethod();  // Target line",
            "    print(x);",
            "  }",
            "}",
            "",
            "void globalFunction() {",
            "  anotherError();  // Another target",
            "}"
        ]
        
        # Test finding method inside class
        function_name = self.fixer._find_containing_function(lines, 5)  # undefinedMethod line
        assert function_name == "myMethod"
        
        # Test finding global function
        function_name = self.fixer._find_containing_function(lines, 11)  # anotherError line
        assert function_name == "globalFunction"
        
        # Test line not in any function
        function_name = self.fixer._find_containing_function(lines, 1)  # import line
        assert function_name is None
    
    def test_extract_dependencies(self):
        """Test extracting dependencies from pubspec.yaml"""
        pubspec_content = """
name: test_project
description: A test project

dependencies:
  flutter:
    sdk: flutter
  http: ^0.13.0
  provider: ^6.0.0
  cupertino_icons: ^1.0.2

dev_dependencies:
  flutter_test:
    sdk: flutter
  flutter_lints: ^2.0.0

flutter:
  uses-material-design: true
"""
        
        dependencies = self.fixer._extract_dependencies(pubspec_content)
        
        assert "flutter" in dependencies
        assert "http" in dependencies
        assert "provider" in dependencies
        assert "cupertino_icons" in dependencies
        # Should not include dev dependencies
        assert "flutter_test" not in dependencies
        assert "flutter_lints" not in dependencies
    
    def test_collect_error_context_with_errors(self):
        """Test collecting error context with actual errors"""
        # Create analysis result with errors
        errors = [
            AnalysisError(
                file_path="lib/main.dart",
                line=27,  # Line with undefinedMethod
                column=25,
                message="The method 'undefinedMethod' isn't defined",
                error_type="error"
            ),
            AnalysisError(
                file_path="lib/main.dart",
                line=33,  # Line with nonExistentFunction
                column=5,
                message="The function 'nonExistentFunction' isn't defined",
                error_type="error"
            )
        ]
        
        analysis_result = AnalysisResult(
            success=False,
            errors=errors,
            warnings=[],
            output="dart analyze output...",
            execution_time=2.0
        )
        
        context = self.fixer._collect_error_context(analysis_result)
        
        # Check that file content was read
        assert "lib/main.dart" in context["files"]
        assert "import 'package:flutter/material.dart';" in context["files"]["lib/main.dart"]
        
        # Check project structure
        assert "package:flutter/material.dart" in context["project_structure"]["imports"]
        assert "package:http/http.dart" in context["project_structure"]["imports"]
        assert "MyApp" in context["project_structure"]["classes"]
        assert "HomePage" in context["project_structure"]["classes"]
        
        # Check dependencies
        assert "flutter" in context["project_structure"]["dependencies"]
        assert "http" in context["project_structure"]["dependencies"]
        assert "provider" in context["project_structure"]["dependencies"]
        
        # Check error context
        error_key_1 = "lib/main.dart:27:25"
        error_key_2 = "lib/main.dart:33:5"
        
        assert error_key_1 in context["error_context"]
        assert error_key_2 in context["error_context"]
        
        # Check specific error context
        error_context_1 = context["error_context"][error_key_1]
        assert "undefinedMethod" in error_context_1["line_content"]
        assert len(error_context_1["surrounding_lines"]) > 0
        assert "fetchData" in error_context_1["function_context"]
    
    def test_collect_error_context_no_errors(self):
        """Test collecting error context when there are no errors"""
        analysis_result = AnalysisResult(
            success=True,
            errors=[],
            warnings=[],
            output="No issues found!",
            execution_time=1.0
        )
        
        context = self.fixer._collect_error_context(analysis_result)
        
        # Should have empty files and error_context
        assert len(context["files"]) == 0
        assert len(context["error_context"]) == 0
        
        # Should still have project structure with dependencies
        assert len(context["project_structure"]["dependencies"]) > 0
        assert "flutter" in context["project_structure"]["dependencies"]
    
    def test_collect_error_context_with_unknown_file(self):
        """Test collecting error context with unknown file paths"""
        errors = [
            AnalysisError(
                file_path="unknown",
                line=0,
                column=0,
                message="Some general error",
                error_type="error"
            )
        ]
        
        analysis_result = AnalysisResult(
            success=False,
            errors=errors,
            warnings=[],
            output="Some error output",
            execution_time=1.0
        )
        
        context = self.fixer._collect_error_context(analysis_result)
        
        # Should not try to read "unknown" file
        assert "unknown" not in context["files"]
        assert len(context["error_context"]) == 0