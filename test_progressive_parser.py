#!/usr/bin/env python3
"""
Test Suite for Progressive JSON Parser
Tests the extraction of file operations from truncated/malformed JSON responses
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from code_modification.services.json_utils import extract_partial_file_operations, extract_shell_commands_from_response


def test_user_example_with_duplicate_paths():
    """Test extraction from the user's actual problematic response"""
    print("🧪 Testing user example with duplicate paths and truncation...")
    
    # Real user response data with duplicate paths and truncation
    response = '''
    "confidence": 95,
    "file_operations": [
        {
            "operation": "create",
            "path": "lib/models/todo_model.dartlib/models/todo_model.dart",
            "content": "class TodoModel {\\n  final String id;\\n  final String title;\\n  final String description;\\n  final bool isCompleted;\\n  final DateTime createdAt;\\n  final DateTime? completedAt;\\n  final String userId;\\n\\n  const TodoModel({\\n    required this.id,\\n    required this.title,\\n    required this.description,\\n    required this.isCompleted,\\n    required this.createdAt,\\n    this.completedAt,\\n    required this.userId,\\n  });\\n\\n  factory TodoModel.fromJson(Map<String, dynamic> json) {\\n    return TodoModel(\\n      id: json['id'] as String,\\n      title: json['title'] as String,\\n      description: json['description'] as String,\\n      isCompleted: json['isCompleted'] as bool,\\n      createdAt: DateTime.parse(json['createdAt'] as String),\\n      completedAt: json['completedAt'] != null\\n          ? DateTime.parse(json['completedAt'] as String)\\n          : null,\\n      userId: json['userId'] as String,\\n    );\\n  }\\n\\n  Map<String, dynamic> toJson() {\\n    return {\\n      'id': id,\\n      'title': title,\\n      'description': description,\\n      'isCompleted': isCompleted,\\n      'createdAt': createdAt.toIso8601String(),\\n      'completedAt': completedAt?.toIso8601String(),\\n      'userId': userId,\\n    };\\n  }\\n}",
            "reason": "Create TodoModel with all necessary properties",
            "validation": "Complete class implementation"
        },
        {
            "operation": "create",
            "path": "lib/services/todo_service.dart",
            "content": "import 'dart:async';\\nimport '../models/todo_model.dart';\\n\\nclass TodoService {\\n  final List<TodoModel> _todos = [];\\n  final StreamController<List<TodoModel>> _todosController =\\n      StreamController<List<TodoModel>>.broadcast();\\n\\n  Stream<List<TodoModel>> get todosStream => _todosController.stream;\\n  List<TodoModel> get todos => List.unmodifiable(_todos);\\n\\n  Future<void> loadTodos(String userId) async {\\n    try {\\n      await Future.delayed(const Duration(milliseconds: 500));\\n      final userTodos = _todos.where((todo) => todo.userId == userId).toList();\\n      _todosController.add(userTodos);\\n    } catch (e) {\\n      throw Exception('Failed to load todos: ${e.toString()}');\\n    }\\n  }\\n}",
            "reason": "Create TodoService for todo management",
            "validation": "Complete service implementation"
        },
        {
            "operation": "create",
            "path": "lib/screens/home_screen.dart",
            "content": "import 'package:flutter/material.dart';\\n\\nclass HomeScreen extends StatefulWidget {\\n  const HomeScreen({super.key});\\n\\n  @override\\n  Widget build(BuildContext context) {\\n    return Scaffold(\\n      appBar: AppBar(title: Text('Home')),\\n      body: Center(child: Text('Welcome')),\\n      floatingActionButton: FloatingActionButton(\\n        onPressed: () {},\\n        child: const Icon(Icons.add),\\▋",
            "reason": "Create home screen",
            "validation": "Incomplete - truncated"
        }
    ]
    '''
    
    operations = extract_partial_file_operations(response)
    
    print(f"   ✅ Extracted {len(operations)} operations")
    
    # Should extract 2 complete operations, skip the truncated one
    extracted_files = [op.get('path') for op in operations]
    print(f"   📁 Extracted files: {extracted_files}")
    
    # Check that duplicate path was fixed
    todo_model_fixed = any('lib/models/todo_model.dart' == path for path in extracted_files)
    print(f"   {'✅ PASS' if todo_model_fixed else '❌ FAIL'}: Duplicate path fixed to lib/models/todo_model.dart")
    
    # Check that truncated file is excluded
    truncated_excluded = not any('home_screen.dart' in path for path in extracted_files)
    print(f"   {'✅ PASS' if truncated_excluded else '❌ FAIL'}: Truncated file correctly excluded")
    
    success = len(operations) >= 2 and todo_model_fixed
    print(f"   {'✅ PASS' if success else '❌ FAIL'}: Expected 2+ complete operations with path fixes")
    
    return success


def test_complete_response_with_truncation():
    """Test extraction from the real user example with 7 complete + 1 truncated operation"""
    print("\\n🧪 Testing complete response with truncation...")
    
    # Real user response data
    response = '''
    "confidence": 98,
    "file_operations": [
        {
            "operation": "modify",
            "path": "lib/main.dart",
            "content": "import 'package:flutter/material.dart';\\nimport 'package:project/screens/login_screen.dart';\\nimport 'package:project/screens/todo_list_screen.dart';\\nimport 'package:project/services/auth_service.dart';\\n\\nvoid main() {\\n  runApp(const MyApp());\\n}\\n\\nclass MyApp extends StatelessWidget {\\n  const MyApp({super.key});\\n\\n  @override\\n  Widget build(BuildContext context) {\\n    return MaterialApp(\\n      title: 'Todo List App',\\n      theme: ThemeData(\\n        colorScheme: ColorScheme.fromSeed(seedColor: Colors.deepPurple),\\n        useMaterial3: true,\\n      ),\\n      home: const AuthWrapper(),\\n      routes: {\\n        '/login': (context) => const LoginScreen(),\\n        '/todos': (context) => const TodoListScreen(),\\n      },\\n    );\\n  }\\n}\\n\\nclass AuthWrapper extends StatelessWidget {\\n  const AuthWrapper({super.key});\\n\\n  @override\\n  Widget build(BuildContext context) {\\n    return FutureBuilder<bool>(\\n      future: AuthService.isLoggedIn(),\\n      builder: (context, snapshot) {\\n        if (snapshot.connectionState == ConnectionState.waiting) {\\n          return const Scaffold(\\n            body: Center(\\n              child: CircularProgressIndicator(),\\n            ),\\n          );\\n        }\\n        \\n        if (snapshot.hasData && snapshot.data == true) {\\n          return const TodoListScreen();\\n        }\\n        \\n        return const LoginScreen();\\n      },\\n    );\\n  }\\n}",
            "reason": "Updated main.dart to support authentication flow and routing",
            "validation": "Perfect Dart syntax with proper imports"
        },
        {
            "operation": "create",
            "path": "lib/screens/login_screen.dart",
            "content": "import 'package:flutter/material.dart';\\nimport 'package:project/services/auth_service.dart';\\nimport 'package:project/widgets/custom_text_field.dart';\\nimport 'package:project/screens/todo_list_screen.dart';\\n\\nclass LoginScreen extends StatefulWidget {\\n  const LoginScreen({super.key});\\n\\n  @override\\n  State<LoginScreen> createState() => _LoginScreenState();\\n}\\n\\nclass _LoginScreenState extends State<LoginScreen> {\\n  final _formKey = GlobalKey<FormState>();\\n  final _emailController = TextEditingController();\\n  final _passwordController = TextEditingController();\\n  bool _isLoading = false;\\n  bool _isSignUp = false;\\n\\n  @override\\n  Widget build(BuildContext context) {\\n    return Scaffold(\\n      body: SafeArea(\\n        child: Column(\\n          children: [\\n            // Login form content\\n          ],\\n        ),\\n      ),\\n    );\\n  }\\n}",
            "reason": "Created login screen with authentication",
            "validation": "Complete implementation"
        },
        {
            "operation": "create",
            "path": "lib/models/todo_model.dart",
            "content": "class Todo {\\n  final String id;\\n  final String title;\\n  final bool isCompleted;\\n  final DateTime createdAt;\\n\\n  Todo({\\n    required this.id,\\n    required this.title,\\n    required this.isCompleted,\\n    required this.createdAt,\\n  });\\n\\n  Map<String, dynamic> toJson() {\\n    return {\\n      'id': id,\\n      'title': title,\\n      'isCompleted': isCompleted,\\n      'createdAt': createdAt.toIso8601String(),\\n    };\\n  }\\n}",
            "reason": "Created Todo model",
            "validation": "Complete model implementation"
        },
        {
            "operation": "create",
            "path": "lib/services/auth_service.dart",
            "content": "class AuthService {\\n  static Future<bool> signIn(String email, String password) async {\\n    // Mock implementation\\n    await Future.delayed(Duration(milliseconds: 500));\\n    return true;\\n  }\\n\\n  static Future<bool> signUp(String email, String password) async {\\n    // Mock implementation\\n    await Future.delayed(Duration(milliseconds: 500));\\n    return true;\\n  }\\n\\n  static Future<void> signOut() async {\\n    // Mock implementation\\n    await Future.delayed(Duration(milliseconds: 200));\\n  }\\n}",
            "reason": "Created authentication service",
            "validation": "Complete service implementation"
        },
        {
            "operation": "create",
            "path": "lib/widgets/custom_text_field.dart",
            "content": "import 'package:flutter/material.dart';\\n\\nclass CustomTextField extends StatelessWidget {\\n  final TextEditingController controller;\\n  final String label;\\n  final bool obscureText;\\n  final TextInputType? keyboardType;\\n  final String? Function(String?)? validator;\\n  final Function(String)? onSubmitted;\\n\\n  const CustomTextField({\\n    super.key,\\n    required this.controller,\\n    required this.label,\\n    this.obscureText = false,\\n    this.keyboardType,\\n    this.validator,\\n    this.onSubmitted,\\n  });\\n\\n  @override\\n  Widget build(BuildContext context) {\\n    return TextFormField(\\n      controller: controller,\\n      obscureText: obscureText,\\n      keyboardType: keyboardType,\\n      validator: validator,\\n      onFieldSubmitted: onSubmitted,\\n      decoration: InputDecoration(\\n        labelText: label,\\n        border: OutlineInputBorder(),\\n      ),\\n    );\\n  }\\n}",
            "reason": "Created custom text field widget",
            "validation": "Complete widget implementation"
        },
        {
            "operation": "create",
            "path": "lib/widgets/incomplete_widget.dart",
            "content": "import 'package:flutter/material.dart';\\nimport 'package:
    '''
    
    operations = extract_partial_file_operations(response)
    
    print(f"   ✅ Extracted {len(operations)} operations")
    
    # Should extract 5 complete operations, skip the incomplete one
    expected_files = [
        "lib/main.dart",
        "lib/screens/login_screen.dart", 
        "lib/models/todo_model.dart",
        "lib/services/auth_service.dart",
        "lib/widgets/custom_text_field.dart"
    ]
    
    extracted_files = [op.get('path') for op in operations]
    print(f"   📁 Expected files: {expected_files}")
    print(f"   📁 Extracted files: {extracted_files}")
    
    success = len(operations) == 5 and all(f in extracted_files for f in expected_files)
    print(f"   {'✅ PASS' if success else '❌ FAIL'}: Expected 5 complete operations")
    
    # Check that incomplete file is not included
    incomplete_not_included = "lib/widgets/incomplete_widget.dart" not in extracted_files
    print(f"   {'✅ PASS' if incomplete_not_included else '❌ FAIL'}: Incomplete file correctly excluded")
    
    return success and incomplete_not_included


def test_single_complete_operation():
    """Test extraction of a single complete file operation"""
    print("\\n🧪 Testing single complete operation...")
    
    response = '''
    {
        "operation": "create",
        "path": "lib/test_file.dart",
        "content": "import 'package:flutter/material.dart';\\n\\nclass TestWidget extends StatelessWidget {\\n  @override\\n  Widget build(BuildContext context) {\\n    return Container();\\n  }\\n}",
        "reason": "Test file creation",
        "validation": "Complete implementation"
    }
    '''
    
    operations = extract_partial_file_operations(response)
    
    success = (len(operations) == 1 and 
              operations[0].get('path') == 'lib/test_file.dart' and
              operations[0].get('operation') == 'create' and
              'TestWidget' in operations[0].get('content', ''))
    
    print(f"   {'✅ PASS' if success else '❌ FAIL'}: Single operation extracted correctly")
    return success


def test_malformed_json_with_complete_objects():
    """Test extraction from malformed JSON that contains complete objects"""
    print("\\n🧪 Testing malformed JSON with complete objects...")
    
    response = '''
    {
        "confidence": 95,
        "file_operations": [
            {
                "operation": "modify",
                "path": "lib/main.dart", 
                "content": "void main() => runApp(MyApp());",
                "reason": "Simplified main"
            },,
            {
                "operation": "create",
                "path": "lib/utils.dart",
                "content": "class Utils {\\n  static String formatDate(DateTime date) {\\n    return date.toString();\\n  }\\n}",
                "reason": "Added utilities"
            },
        ]
    '''
    
    operations = extract_partial_file_operations(response)
    
    success = (len(operations) >= 1 and
              any(op.get('path') == 'lib/main.dart' for op in operations))
    
    print(f"   ✅ Extracted {len(operations)} operations from malformed JSON")
    print(f"   {'✅ PASS' if success else '❌ FAIL'}: At least main.dart extracted correctly")
    return success


def test_truncated_mid_content():
    """Test extraction when response is cut off in the middle of content"""
    print("\\n🧪 Testing truncation mid-content...")
    
    response = '''
    {
        "file_operations": [
            {
                "operation": "create",
                "path": "lib/complete_file.dart",
                "content": "class CompleteFile { void method() {} }",
                "reason": "Complete file"
            },
            {
                "operation": "create", 
                "path": "lib/incomplete_file.dart",
                "content": "class IncompleteFile { void method() { print('This content is cut off and
    '''
    
    operations = extract_partial_file_operations(response)
    
    success = (len(operations) == 1 and
              operations[0].get('path') == 'lib/complete_file.dart')
    
    print(f"   ✅ Extracted {len(operations)} operations")
    print(f"   {'✅ PASS' if success else '❌ FAIL'}: Only complete file extracted")
    return success


def test_no_file_operations():
    """Test extraction from response with no file operations"""
    print("\\n🧪 Testing response with no file operations...")
    
    response = '''
    {
        "analysis": "No changes needed",
        "confidence": 100,
        "shell_commands": ["flutter pub get"],
        "message": "Everything looks good"
    }
    '''
    
    operations = extract_partial_file_operations(response)
    
    success = len(operations) == 0
    
    print(f"   {'✅ PASS' if success else '❌ FAIL'}: No operations extracted from response without file_operations")
    return success


def test_shell_command_extraction():
    """Test extraction of shell commands"""
    print("\\n🧪 Testing shell command extraction...")
    
    response = '''
    {
        "file_operations": [],
        "shell_commands": [
            "flutter pub add http",
            "flutter pub get",
            "dart format ."
        ]
    }
    '''
    
    commands = extract_shell_commands_from_response(response)
    
    expected_commands = ["flutter pub add http", "flutter pub get", "dart format ."]
    success = commands == expected_commands
    
    print(f"   ✅ Extracted commands: {commands}")
    print(f"   {'✅ PASS' if success else '❌ FAIL'}: All shell commands extracted correctly")
    return success


def run_all_tests():
    """Run all tests and report results"""
    print("🚀 Starting Progressive JSON Parser Tests\\n")
    
    tests = [
        test_user_example_with_duplicate_paths,
        test_complete_response_with_truncation,
        test_single_complete_operation, 
        test_malformed_json_with_complete_objects,
        test_truncated_mid_content,
        test_no_file_operations,
        test_shell_command_extraction
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results.append(False)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Progressive parser is working correctly.")
    else:
        print("❌ Some tests failed. Please check the implementation.")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)