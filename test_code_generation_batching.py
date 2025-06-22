#!/usr/bin/env python3
"""
Comprehensive tests for 100+ file code generation batching behavior
Tests the iterative processing, partial success handling, and retry logic
"""

import sys
import asyncio
import json
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, List, Set

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from code_modification.code_modifier import CodeModificationService, ModificationRequest
from code_modification.llm_executor import SimpleLLMExecutor, LLMResponse, TokenUsage

class MockLLMExecutor:
    """Mock LLM executor that simulates realistic batching behavior"""
    
    def __init__(self):
        self.call_count = 0
        self.responses = []
        self.failure_rate = 0.1  # 10% of files fail per attempt
        self.max_files_per_batch = 12  # Realistic batch size
        self.min_files_per_batch = 3   # Minimum for complex files
        self.intermittent_failures = []  # Initialize empty list
        
    def set_failure_scenarios(self, scenarios: Dict[str, any]):
        """Configure different failure scenarios for testing"""
        self.failure_rate = scenarios.get('failure_rate', 0.1)
        self.max_files_per_batch = scenarios.get('max_batch_size', 12)
        self.intermittent_failures = scenarios.get('intermittent_failures', [])
        
    def execute(self, messages, system_prompt=None, **kwargs):
        """Mock LLM execution with realistic batching simulation"""
        self.call_count += 1
        
        # Extract target files from the user prompt
        user_content = messages[0]['content'][0]['text'] if messages else ""
        target_files = self._extract_target_files(user_content)
        
        # Simulate realistic batch processing
        batch_size = min(len(target_files), self.max_files_per_batch)
        if self.call_count > 5:  # Later attempts handle fewer files
            batch_size = min(batch_size, self.min_files_per_batch)
            
        # Simulate some files failing randomly
        successful_files = []
        failed_files = []
        
        for i, file_path in enumerate(target_files[:batch_size]):
            # Simulate failure scenarios
            should_fail = (
                # Random failure based on failure rate
                (hash(file_path + str(self.call_count)) % 100) < (self.failure_rate * 100) or
                # Specific intermittent failures
                (file_path in self.intermittent_failures and self.call_count < 3) or
                # Complex files that fail multiple times
                ('complex' in file_path and self.call_count < 4)
            )
            
            if should_fail:
                failed_files.append(file_path)
            else:
                successful_files.append(file_path)
        
        # Generate mock response
        response_data = self._generate_mock_response(successful_files, failed_files)
        
        # Simulate token usage
        usage = TokenUsage(
            input=len(user_content) // 4,  # Rough token estimation
            output=len(response_data) // 4,
            cache_creation=0,
            cache_read=0
        )
        
        return LLMResponse(
            text=response_data,
            usage=usage,
            model="claude-sonnet-4-20250514"
        )
    
    def _extract_target_files(self, user_content: str) -> List[str]:
        """Extract target files from user prompt"""
        import re
        
        # Look for JSON arrays in the prompt
        file_arrays = re.findall(r'"target_files":\s*(\[.*?\])', user_content, re.DOTALL)
        if not file_arrays:
            file_arrays = re.findall(r'"files_to_create":\s*(\[.*?\])', user_content, re.DOTALL)
        
        if file_arrays:
            try:
                files = json.loads(file_arrays[0])
                return files if isinstance(files, list) else []
            except:
                pass
                
        # Fallback: extract from context
        files = re.findall(r'lib/[^"\s]+\.dart', user_content)
        return list(set(files))[:20]  # Limit for testing
    
    def _generate_mock_response(self, successful_files: List[str], failed_files: List[str]) -> str:
        """Generate realistic JSON response"""
        file_operations = []
        
        for file_path in successful_files:
            # Generate appropriate content based on file type
            content = self._generate_file_content(file_path)
            
            file_operations.append({
                "operation": "create" if "new_" in file_path else "modify",
                "path": file_path,
                "content": content,
                "reason": f"Generated {file_path} based on requirements",
                "validation": "Syntax check passed"
            })
        
        # For failed files, they just won't appear in the response
        # This simulates the LLM not generating them due to complexity/token limits
        
        response = {
            "analysis": f"Generated {len(successful_files)} files successfully. {len(failed_files)} files need retry due to complexity.",
            "confidence": max(70, 95 - (len(failed_files) * 5)),
            "file_operations": file_operations,
            "shell_commands": [
                "flutter pub get",
                "dart format ."
            ] if successful_files else [],
            "dependencies_added": [],
            "architecture_notes": "Maintaining existing Flutter architecture patterns"
        }
        
        return json.dumps(response, indent=2)
    
    def _generate_file_content(self, file_path: str) -> str:
        """Generate realistic Dart file content based on path"""
        if "model" in file_path:
            return f"""import 'package:flutter/foundation.dart';

class {self._get_class_name(file_path)} {{
  final String id;
  final String name;
  
  const {self._get_class_name(file_path)}({{
    required this.id,
    required this.name,
  }});
  
  Map<String, dynamic> toJson() => {{
    'id': id,
    'name': name,
  }};
  
  factory {self._get_class_name(file_path)}.fromJson(Map<String, dynamic> json) => {self._get_class_name(file_path)}(
    id: json['id'],
    name: json['name'],
  );
}}"""
        
        elif "screen" in file_path:
            return f"""import 'package:flutter/material.dart';

class {self._get_class_name(file_path)} extends StatefulWidget {{
  const {self._get_class_name(file_path)}({{Key? key}}) : super(key: key);

  @override
  State<{self._get_class_name(file_path)}> createState() => _{self._get_class_name(file_path)}State();
}}

class _{self._get_class_name(file_path)}State extends State<{self._get_class_name(file_path)}> {{
  @override
  Widget build(BuildContext context) {{
    return Scaffold(
      appBar: AppBar(
        title: const Text('{self._get_class_name(file_path)}'),
      ),
      body: const Center(
        child: Text('Welcome to {self._get_class_name(file_path)}'),
      ),
    );
  }}
}}"""
        
        elif "widget" in file_path:
            return f"""import 'package:flutter/material.dart';

class {self._get_class_name(file_path)} extends StatelessWidget {{
  const {self._get_class_name(file_path)}({{Key? key}}) : super(key: key);

  @override
  Widget build(BuildContext context) {{
    return Container(
      child: const Text('{self._get_class_name(file_path)}'),
    );
  }}
}}"""
        
        elif "service" in file_path:
            return f"""import 'dart:async';

class {self._get_class_name(file_path)} {{
  static final {self._get_class_name(file_path)} _instance = {self._get_class_name(file_path)}._internal();
  factory {self._get_class_name(file_path)}() => _instance;
  {self._get_class_name(file_path)}._internal();

  Future<void> initialize() async {{
    // Initialize service
  }}
  
  Future<List<String>> getData() async {{
    // Fetch data
    return ['data1', 'data2'];
  }}
}}"""
        
        else:
            return f"""import 'package:flutter/material.dart';

class {self._get_class_name(file_path)} {{
  // Generated content for {file_path}
  
  void performAction() {{
    print('Action performed in {file_path}');
  }}
}}"""
    
    def _get_class_name(self, file_path: str) -> str:
        """Convert file path to class name"""
        name = Path(file_path).stem
        # Convert snake_case to PascalCase
        return ''.join(word.capitalize() for word in name.split('_'))

    def is_available(self) -> bool:
        return True


class CodeGenerationBatchingTests:
    """Comprehensive test suite for code generation batching behavior"""
    
    def __init__(self):
        self.test_project_path = "./test_project"
        self.mock_llm = MockLLMExecutor()
        
    async def test_100_files_iterative_processing(self):
        """Test that 100 files are processed iteratively, not in a single call"""
        print("🧪 Testing 100 Files Iterative Processing...")
        
        # Create 100 test files
        test_files = self._generate_test_file_list(100)
        
        # Mock the CodeModificationService
        with patch('code_modification.code_modifier.SimpleLLMExecutor', return_value=self.mock_llm):
            service = CodeModificationService(self.test_project_path)
            
            # Create modification request
            request = ModificationRequest(
                description="Generate 100 Flutter files for a complete app",
                files_to_create=test_files,
                max_retries=20
            )
            
            # Execute the generation
            start_time = time.time()
            result = await service.modify_code(request)
            duration = time.time() - start_time
            
            # Validate iterative behavior
            print(f"📊 Total LLM calls made: {self.mock_llm.call_count}")
            print(f"📊 Total duration: {duration:.2f}s")
            print(f"📊 Files requested: {len(test_files)}")
            print(f"📊 Files generated: {len(result.modified_files)}")
            print(f"📊 Success rate: {len(result.modified_files)/len(test_files)*100:.1f}%")
            
            # Assertions
            assert self.mock_llm.call_count > 1, f"Expected multiple LLM calls, got {self.mock_llm.call_count}"
            assert self.mock_llm.call_count <= 20, f"Too many calls: {self.mock_llm.call_count}"
            assert len(result.modified_files) >= len(test_files) * 0.8, f"Success rate too low: {len(result.modified_files)}/{len(test_files)}"
            
            print("✅ 100 Files Iterative Processing: PASSED")
            return True
    
    async def test_partial_success_handling(self):
        """Test that partial successes are handled correctly"""
        print("\n🧪 Testing Partial Success Handling...")
        
        # Configure mock for partial failures
        self.mock_llm.set_failure_scenarios({
            'failure_rate': 0.3,  # 30% failure rate
            'max_batch_size': 8,
            'intermittent_failures': ['lib/complex_screen.dart', 'lib/advanced_service.dart']
        })
        
        test_files = self._generate_test_file_list(25)
        
        with patch('code_modification.code_modifier.SimpleLLMExecutor', return_value=self.mock_llm):
            service = CodeModificationService(self.test_project_path)
            
            request = ModificationRequest(
                description="Generate files with some complex ones that should fail initially",
                files_to_create=test_files,
                max_retries=15
            )
            
            result = await service.modify_code(request)
            
            print(f"📊 LLM calls made: {self.mock_llm.call_count}")
            print(f"📊 Files generated: {len(result.modified_files)}")
            print(f"📊 Partial success handling working: {result.success}")
            
            # Validate partial success behavior
            assert self.mock_llm.call_count >= 3, f"Expected multiple attempts due to failures, got {self.mock_llm.call_count}"
            assert len(result.modified_files) > 0, "Should have some successful files even with failures"
            
            print("✅ Partial Success Handling: PASSED")
            return True
    
    async def test_retry_logic_for_failed_files(self):
        """Test that failed files are retried in subsequent attempts"""
        print("\n🧪 Testing Retry Logic for Failed Files...")
        
        # Reset mock for this test
        self.mock_llm = MockLLMExecutor()
        self.mock_llm.set_failure_scenarios({
            'failure_rate': 0.4,  # High failure rate initially
            'max_batch_size': 5,
            'intermittent_failures': ['lib/retry_test_1.dart', 'lib/retry_test_2.dart']
        })
        
        test_files = [
            'lib/retry_test_1.dart',
            'lib/retry_test_2.dart', 
            'lib/simple_widget.dart',
            'lib/easy_model.dart',
            'lib/basic_screen.dart'
        ]
        
        with patch('code_modification.code_modifier.SimpleLLMExecutor', return_value=self.mock_llm):
            service = CodeModificationService(self.test_project_path)
            
            request = ModificationRequest(
                description="Test retry logic with specific failing files",
                files_to_create=test_files,
                max_retries=10
            )
            
            result = await service.modify_code(request)
            
            print(f"📊 Total attempts: {self.mock_llm.call_count}")
            print(f"📊 Final success rate: {len(result.files_modified)}/{len(test_files)}")
            
            # Validate retry behavior
            assert self.mock_llm.call_count >= 3, f"Expected retries, got {self.mock_llm.call_count} attempts"
            
            # The intermittent failures should eventually succeed after attempt 3
            successful_files = result.modified_files
            assert 'lib/simple_widget.dart' in successful_files, "Simple files should succeed"
            
            print("✅ Retry Logic for Failed Files: PASSED")
            return True
    
    async def test_token_limit_batching(self):
        """Test that batching respects token limits"""
        print("\n🧪 Testing Token Limit Batching...")
        
        # Simulate token-constrained environment
        self.mock_llm = MockLLMExecutor()
        self.mock_llm.set_failure_scenarios({
            'failure_rate': 0.05,  # Low failure rate
            'max_batch_size': 6,    # Small batches due to "token limits"
        })
        
        test_files = self._generate_test_file_list(30)
        
        with patch('code_modification.code_modifier.SimpleLLMExecutor', return_value=self.mock_llm):
            service = CodeModificationService(self.test_project_path)
            
            request = ModificationRequest(
                description="Test token-limited batching with 30 files",
                files_to_create=test_files,
                max_retries=15
            )
            
            result = await service.modify_code(request)
            
            # Calculate average batch size
            avg_batch_size = len(test_files) / self.mock_llm.call_count if self.mock_llm.call_count > 0 else 0
            
            print(f"📊 LLM calls: {self.mock_llm.call_count}")
            print(f"📊 Average batch size: {avg_batch_size:.1f}")
            print(f"📊 Success rate: {len(result.modified_files)}/{len(test_files)}")
            
            # Validate batching behavior
            assert avg_batch_size <= 8, f"Batch size too large: {avg_batch_size}"
            assert self.mock_llm.call_count >= 5, f"Expected multiple small batches, got {self.mock_llm.call_count}"
            
            print("✅ Token Limit Batching: PASSED")
            return True
    
    async def test_progress_tracking(self):
        """Test that progress is tracked correctly throughout the process"""
        print("\n🧪 Testing Progress Tracking...")
        
        progress_updates = []
        
        # Mock the print function to capture progress updates
        original_print = print
        def mock_print(*args, **kwargs):
            if args and isinstance(args[0], str):
                if "Generation attempt" in args[0] or "Successfully processed" in args[0] or "Remaining files" in args[0]:
                    progress_updates.append(args[0])
            return original_print(*args, **kwargs)
        
        self.mock_llm = MockLLMExecutor()
        test_files = self._generate_test_file_list(15)
        
        with patch('code_modification.code_modifier.SimpleLLMExecutor', return_value=self.mock_llm):
            with patch('builtins.print', side_effect=mock_print):
                service = CodeModificationService(self.test_project_path)
                
                request = ModificationRequest(
                    description="Test progress tracking",
                    files_to_create=test_files,
                    max_retries=10
                )
                
                result = await service.modify_code(request)
        
        print(f"📊 Progress updates captured: {len(progress_updates)}")
        for update in progress_updates:
            print(f"  📋 {update}")
        
        # Validate progress tracking
        generation_attempts = [u for u in progress_updates if "Generation attempt" in u]
        success_updates = [u for u in progress_updates if "Successfully processed" in u]
        
        assert len(generation_attempts) >= 1, "Should have generation attempt updates"
        assert len(success_updates) >= 1, "Should have success updates"
        
        print("✅ Progress Tracking: PASSED")
        return True
    
    async def test_edge_cases(self):
        """Test edge cases like empty responses, malformed JSON, etc."""
        print("\n🧪 Testing Edge Cases...")
        
        # Create a mock that sometimes returns malformed responses
        class EdgeCaseMockLLM(MockLLMExecutor):
            def __init__(self):
                super().__init__()
                self.edge_case_responses = [
                    "",  # Empty response
                    "Invalid JSON {",  # Malformed JSON
                    '{"file_operations": []}',  # Valid but empty
                    '{"analysis": "test"}',  # Missing file_operations
                ]
                self.edge_case_index = 0
                
            def execute(self, messages, system_prompt=None, **kwargs):
                # Return edge case responses for first few calls
                if self.edge_case_index < len(self.edge_case_responses):
                    response_text = self.edge_case_responses[self.edge_case_index]
                    self.edge_case_index += 1
                    
                    return LLMResponse(
                        text=response_text,
                        usage=TokenUsage(input=100, output=50),
                        model="claude-sonnet-4-20250514"
                    )
                else:
                    # Fall back to normal behavior
                    return super().execute(messages, system_prompt, **kwargs)
        
        edge_mock = EdgeCaseMockLLM()
        test_files = ['lib/test_file_1.dart', 'lib/test_file_2.dart']
        
        with patch('code_modification.code_modifier.SimpleLLMExecutor', return_value=edge_mock):
            service = CodeModificationService(self.test_project_path)
            
            request = ModificationRequest(
                description="Test edge case handling",
                files_to_create=test_files,
                max_retries=10
            )
            
            result = await service.modify_code(request)
            
            print(f"📊 Total attempts (including edge cases): {edge_mock.call_count}")
            print(f"📊 Edge cases handled gracefully: {edge_mock.call_count > 4}")
            
            # The system should recover from edge cases and eventually succeed
            assert edge_mock.call_count > 4, "Should have made multiple attempts to handle edge cases"
            assert not result.success or len(result.files_modified) > 0, "Should either fail gracefully or succeed"
            
            print("✅ Edge Cases: PASSED")
            return True
    
    def _generate_test_file_list(self, count: int) -> List[str]:
        """Generate a realistic list of test files"""
        file_types = [
            ('model', 'lib/models/'),
            ('screen', 'lib/screens/'),
            ('widget', 'lib/widgets/'),
            ('service', 'lib/services/'),
            ('controller', 'lib/controllers/'),
            ('util', 'lib/utils/'),
        ]
        
        files = []
        for i in range(count):
            file_type, path = file_types[i % len(file_types)]
            
            # Add some complexity indicators
            complexity = ""
            if i % 10 == 0:  # Every 10th file is complex
                complexity = "complex_"
            elif i % 15 == 0:  # Every 15th file is new
                complexity = "new_"
            
            filename = f"{complexity}{file_type}_{i // len(file_types) + 1}.dart"
            files.append(f"{path}{filename}")
        
        return files
    
    async def run_all_tests(self):
        """Run all batching tests"""
        print("🚀 Starting Code Generation Batching Tests\n")
        
        tests = [
            ("100 Files Iterative Processing", self.test_100_files_iterative_processing),
            ("Partial Success Handling", self.test_partial_success_handling),
            ("Retry Logic for Failed Files", self.test_retry_logic_for_failed_files),
            ("Token Limit Batching", self.test_token_limit_batching),
            ("Progress Tracking", self.test_progress_tracking),
            ("Edge Cases", self.test_edge_cases),
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"{'='*60}")
            print(f"🧪 {test_name}")
            print(f"{'='*60}")
            
            try:
                success = await test_func()
                results.append((test_name, success))
                print(f"{'✅' if success else '❌'} {test_name}: {'PASSED' if success else 'FAILED'}")
            except Exception as e:
                print(f"❌ {test_name}: FAILED with exception: {e}")
                results.append((test_name, False))
            
            # Reset mock for next test
            self.mock_llm = MockLLMExecutor()
            print()
        
        # Summary
        print(f"{'='*60}")
        print("📊 BATCHING TEST SUMMARY")
        print(f"{'='*60}")
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for test_name, success in results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{status:<12} {test_name}")
        
        print(f"\n🎯 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All batching tests passed! The 100+ file generation system is working correctly!")
            print("\n💡 Validated Behaviors:")
            print("• Iterative batch processing instead of single massive calls")
            print("• Partial success handling with file-by-file tracking")
            print("• Smart retry logic for failed files only")
            print("• Token-aware dynamic batch sizing")
            print("• Real-time progress tracking and updates")
            print("• Graceful handling of edge cases and malformed responses")
        else:
            print("⚠️  Some batching tests failed. Check the implementation.")
        
        return passed == total


async def main():
    """Run the batching tests"""
    tester = CodeGenerationBatchingTests()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    import asyncio
    exit_code = asyncio.run(main())
    sys.exit(exit_code)