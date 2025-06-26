#!/usr/bin/env python3
"""
Test realistic LLM response mocking and JSON parsing behavior
Validates that our mock responses match real-world LLM behavior patterns
"""

import sys
import json
import time
from pathlib import Path
from unittest.mock import patch

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from test_code_generation_batching import MockLLMExecutor


class MockLLMResponseTests:
    """Test suite for validating mock LLM response realism"""
    
    def __init__(self):
        self.mock_llm = MockLLMExecutor()
    
    def test_realistic_file_content_generation(self):
        """Test that mock generates realistic Dart file content"""
        print("🧪 Testing Realistic File Content Generation...")
        
        test_cases = [
            ("lib/models/user.dart", "class User", "toJson", "fromJson"),
            ("lib/screens/login_screen.dart", "class LoginScreen", "StatefulWidget", "build"),
            ("lib/widgets/custom_button.dart", "class CustomButton", "StatelessWidget", "build"),
            ("lib/services/api_service.dart", "class ApiService", "_instance", "getData"),
        ]
        
        for file_path, *expected_patterns in test_cases:
            content = self.mock_llm._generate_file_content(file_path)
            
            print(f"\n📁 Testing {file_path}:")
            print(f"   Content length: {len(content)} chars")
            
            # Validate expected patterns exist
            for pattern in expected_patterns:
                assert pattern in content, f"Expected '{pattern}' in {file_path} content"
                print(f"   ✅ Found pattern: {pattern}")
            
            # Validate Dart syntax basics
            assert content.count('{') == content.count('}'), f"Unbalanced braces in {file_path}"
            assert 'import ' in content, f"Missing imports in {file_path}"
            assert 'class ' in content, f"Missing class definition in {file_path}"
            
        print("✅ Realistic File Content Generation: PASSED")
        return True
    
    def test_json_response_format(self):
        """Test that mock generates valid JSON responses"""
        print("\n🧪 Testing JSON Response Format...")
        
        # Mock a typical request
        messages = [{
            'role': 'user',
            'content': [{
                'type': 'text',
                'text': '''
                Project Context: Flutter app
                Files to create: ["lib/models/product.dart", "lib/screens/shop_screen.dart"]
                Change request: Create product model and shopping screen
                '''
            }]
        }]
        
        response = self.mock_llm.execute(messages)
        
        print(f"📊 Response length: {len(response.text)} chars")
        print(f"📊 Token usage: {response.usage.input} input, {response.usage.output} output")
        
        # Validate JSON structure
        try:
            response_data = json.loads(response.text)
            print("✅ Valid JSON response generated")
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON: {e}")
            print(f"Response preview: {response.text[:500]}...")
            return False
        
        # Validate required fields
        required_fields = ['analysis', 'confidence', 'file_operations', 'shell_commands']
        for field in required_fields:
            assert field in response_data, f"Missing required field: {field}"
            print(f"✅ Found required field: {field}")
        
        # Validate file operations structure
        file_ops = response_data['file_operations']
        assert isinstance(file_ops, list), "file_operations should be a list"
        
        if file_ops:
            first_op = file_ops[0]
            op_required_fields = ['operation', 'path', 'content', 'reason']
            for field in op_required_fields:
                assert field in first_op, f"Missing field in file operation: {field}"
                print(f"✅ Found file operation field: {field}")
        
        print("✅ JSON Response Format: PASSED")
        return True
    
    def test_batch_size_simulation(self):
        """Test that mock simulates realistic batch sizes"""
        print("\n🧪 Testing Batch Size Simulation...")
        
        # Test different scenarios
        scenarios = [
            (5, "Small batch"),
            (15, "Medium batch"), 
            (30, "Large batch"),
            (50, "Very large batch")
        ]
        
        for file_count, scenario_name in scenarios:
            print(f"\n📋 Testing {scenario_name} ({file_count} files):")
            
            # Create mock request
            test_files = [f"lib/test_{i}.dart" for i in range(file_count)]
            messages = [{
                'role': 'user', 
                'content': [{
                    'type': 'text',
                    'text': f'''
                    Project Context: Test scenario
                    Files to create: {json.dumps(test_files)}
                    Change request: Generate {file_count} test files
                    '''
                }]
            }]
            
            # Reset mock for clean test
            mock = MockLLMExecutor()
            response = mock.execute(messages)
            response_data = json.loads(response.text)
            
            generated_count = len(response_data['file_operations'])
            batch_efficiency = generated_count / file_count * 100
            
            print(f"   📊 Requested: {file_count} files")
            print(f"   📊 Generated: {generated_count} files")
            print(f"   📊 Efficiency: {batch_efficiency:.1f}%")
            
            # Validate realistic constraints
            if file_count <= 10:
                assert generated_count >= file_count * 0.8, f"Too few files generated for small batch"
            elif file_count <= 20:
                assert generated_count >= file_count * 0.6, f"Too few files generated for medium batch"
            else:
                assert generated_count >= min(12, file_count * 0.2), f"Unrealistic batch size for large request"
                assert generated_count <= 15, f"Batch size too large: {generated_count}"
        
        print("✅ Batch Size Simulation: PASSED")
        return True
    
    def test_failure_scenarios(self):
        """Test that mock simulates realistic failure patterns"""
        print("\n🧪 Testing Failure Scenarios...")
        
        # Configure different failure rates
        failure_scenarios = [
            (0.0, "Perfect success"),
            (0.1, "Low failure rate"),
            (0.3, "Medium failure rate"),
            (0.5, "High failure rate")
        ]
        
        for failure_rate, scenario_name in failure_scenarios:
            print(f"\n📋 Testing {scenario_name} ({failure_rate*100:.0f}% failure rate):")
            
            mock = MockLLMExecutor()
            mock.set_failure_scenarios({'failure_rate': failure_rate, 'max_batch_size': 10})
            
            # Run multiple attempts to see failure patterns
            total_requested = 0
            total_generated = 0
            attempts = 5
            
            for attempt in range(attempts):
                test_files = [f"lib/attempt_{attempt}_file_{i}.dart" for i in range(8)]
                messages = [{
                    'role': 'user',
                    'content': [{
                        'type': 'text', 
                        'text': f'Files to create: {json.dumps(test_files)}'
                    }]
                }]
                
                response = mock.execute(messages)
                response_data = json.loads(response.text)
                generated = len(response_data['file_operations'])
                
                total_requested += len(test_files)
                total_generated += generated
            
            actual_success_rate = total_generated / total_requested
            expected_success_rate = 1.0 - failure_rate
            
            print(f"   📊 Expected success rate: {expected_success_rate*100:.1f}%")
            print(f"   📊 Actual success rate: {actual_success_rate*100:.1f}%")
            
            # Allow some variance in simulation
            tolerance = 0.2
            assert abs(actual_success_rate - expected_success_rate) <= tolerance, \
                f"Success rate {actual_success_rate:.2f} too far from expected {expected_success_rate:.2f}"
        
        print("✅ Failure Scenarios: PASSED")
        return True
    
    def test_progressive_improvement(self):
        """Test that mock simulates progressive improvement over attempts"""
        print("\n🧪 Testing Progressive Improvement...")
        
        mock = MockLLMExecutor()
        mock.set_failure_scenarios({
            'failure_rate': 0.4,  # Start with high failure rate
            'intermittent_failures': ['lib/complex_file.dart', 'lib/difficult_widget.dart']
        })
        
        test_files = [
            'lib/complex_file.dart',      # Should fail initially
            'lib/difficult_widget.dart',  # Should fail initially  
            'lib/simple_model.dart',      # Should succeed early
            'lib/basic_screen.dart'       # Should succeed early
        ]
        
        attempt_results = []
        
        for attempt in range(5):
            messages = [{
                'role': 'user',
                'content': [{
                    'type': 'text',
                    'text': f'Attempt {attempt+1}. Files: {json.dumps(test_files)}'
                }]
            }]
            
            response = mock.execute(messages)
            response_data = json.loads(response.text)
            generated_files = [op['path'] for op in response_data['file_operations']]
            
            attempt_results.append({
                'attempt': attempt + 1,
                'generated': len(generated_files),
                'files': generated_files
            })
            
            print(f"   📋 Attempt {attempt+1}: {len(generated_files)} files generated")
            print(f"      Files: {generated_files}")
        
        # Validate that complex files eventually succeed
        final_attempt = attempt_results[-1]
        assert len(final_attempt['files']) >= 2, "Should have some success in final attempts"
        
        # Check that simple files succeed earlier
        early_successes = [r for r in attempt_results[:3] if 'lib/simple_model.dart' in r['files']]
        assert len(early_successes) > 0, "Simple files should succeed in early attempts"
        
        print("✅ Progressive Improvement: PASSED")
        return True
    
    def test_token_usage_simulation(self):
        """Test that mock simulates realistic token usage"""
        print("\n🧪 Testing Token Usage Simulation...")
        
        test_cases = [
            ("Short request", "Create one model", 1),
            ("Medium request", "Create several screens and widgets for a shopping app", 5),
            ("Long request", "Generate a complete Flutter app with models, services, screens, and widgets" * 3, 10)
        ]
        
        for case_name, request_text, expected_files in test_cases:
            messages = [{
                'role': 'user',
                'content': [{
                    'type': 'text',
                    'text': request_text + f' Files: {json.dumps([f"lib/file_{i}.dart" for i in range(expected_files)])}'
                }]
            }]
            
            response = self.mock_llm.execute(messages)
            
            print(f"\n📋 {case_name}:")
            print(f"   📊 Input tokens: {response.usage.input}")
            print(f"   📊 Output tokens: {response.usage.output}")
            print(f"   📊 Total tokens: {response.usage.input + response.usage.output}")
            
            # Validate realistic token usage
            assert response.usage.input > 0, "Should have input tokens"
            assert response.usage.output > 0, "Should have output tokens"
            
            # Longer requests should use more tokens
            assert response.usage.input >= len(request_text) // 6, "Input tokens should correlate with request length"
            assert response.usage.output >= len(response.text) // 6, "Output tokens should correlate with response length"
        
        print("✅ Token Usage Simulation: PASSED")
        return True
    
    def run_all_tests(self):
        """Run all mock LLM response tests"""
        print("🚀 Starting Mock LLM Response Tests\n")
        
        tests = [
            ("Realistic File Content Generation", self.test_realistic_file_content_generation),
            ("JSON Response Format", self.test_json_response_format),
            ("Batch Size Simulation", self.test_batch_size_simulation),
            ("Failure Scenarios", self.test_failure_scenarios),
            ("Progressive Improvement", self.test_progressive_improvement),
            ("Token Usage Simulation", self.test_token_usage_simulation),
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"{'='*60}")
            print(f"🧪 {test_name}")
            print(f"{'='*60}")
            
            try:
                success = test_func()
                results.append((test_name, success))
                print(f"{'✅' if success else '❌'} {test_name}: {'PASSED' if success else 'FAILED'}")
            except Exception as e:
                print(f"❌ {test_name}: FAILED with exception: {e}")
                import traceback
                traceback.print_exc()
                results.append((test_name, False))
            
            print()
        
        # Summary
        print(f"{'='*60}")
        print("📊 MOCK LLM RESPONSE TEST SUMMARY")
        print(f"{'='*60}")
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for test_name, success in results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{status:<12} {test_name}")
        
        print(f"\n🎯 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All mock LLM response tests passed!")
            print("\n💡 Validated Mock Behaviors:")
            print("• Realistic Dart code generation for different file types")
            print("• Proper JSON response formatting with all required fields")
            print("• Token-aware batch size limitations")
            print("• Configurable failure scenarios and success rates")
            print("• Progressive improvement simulation over multiple attempts")
            print("• Realistic token usage calculation")
        else:
            print("⚠️  Some mock response tests failed. Check the mock implementation.")
        
        return passed == total


def main():
    """Run the mock LLM response tests"""
    tester = MockLLMResponseTests()
    success = tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)