#!/usr/bin/env python3
"""
Test Suite for Dart Analysis Parsing
Tests the parsing of dart analyze JSON output
"""

import sys
import os
import json
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from code_modification.services.code_modifier import DartAnalysisIssue, DartAnalysisResult, CodeModificationService
from pathlib import Path

def test_parse_real_dart_analyze_output():
    """Test parsing the actual dart analyze JSON output you provided"""
    print("🧪 Testing real dart analyze JSON output parsing...")
    
    # Your actual dart analyze output
    real_output = '''{"version":1,"diagnostics":[{"code":"missing_default_value_for_parameter","severity":"ERROR","type":"COMPILE_TIME_ERROR","location":{"file":"/mnt/c/Users/user/code/walturn/flutter-server/project/lib/models/invalid_model.dart","range":{"start":{"offset":151,"line":9,"column":22},"end":{"offset":155,"line":9,"column":26}}},"problemMessage":"The parameter 'name' can't have a value of 'null' because of its type, but the implicit default value is 'null'.","correctionMessage":"Try adding either an explicit non-'null' default value or the 'required' modifier.","documentation":"https://dart.dev/diagnostics/missing_default_value_for_parameter"},{"code":"undefined_method","severity":"ERROR","type":"COMPILE_TIME_ERROR","location":{"file":"/mnt/c/Users/user/code/walturn/flutter-server/project/lib/models/invalid_model.dart","range":{"start":{"offset":377,"line":17,"column":21},"end":{"offset":385,"line":17,"column":29}}},"problemMessage":"The method 'getValue' isn't defined for the type 'InvalidModel'.","correctionMessage":"Try correcting the name to the name of an existing method, or defining a method named 'getValue'.","documentation":"https://dart.dev/diagnostics/undefined_method"}]}'''
    
    # Create a test instance
    test_project_path = "/tmp/test_project"
    modifier = CodeModificationService(test_project_path)
    
    # Test the parsing
    result = modifier._parse_dart_analyze_output(real_output, "", 1)  # non-zero return code
    
    print(f"   ✅ Parsed {len(result.errors)} errors")
    print(f"   ✅ Parsed {len(result.warnings)} warnings")
    print(f"   ✅ Success: {result.success}")
    print(f"   ✅ Error message: {result.error_message}")
    
    # Check specific errors
    for i, error in enumerate(result.errors[:3]):  # Show first 3
        print(f"   📋 Error {i+1}: {error.file_path}:{error.line} - {error.message}")
    
    # Should find at least 2 errors from the sample
    success = len(result.errors) >= 2
    print(f"   {'✅ PASS' if success else '❌ FAIL'}: Found expected errors")
    
    return success

def test_parse_complex_dart_output():
    """Test parsing more complex output with errors and warnings"""
    print("\n🧪 Testing complex dart analyze output...")
    
    # Simulated complex output with multiple types
    complex_output = '''{"version":1,"diagnostics":[
{"code":"missing_default_value_for_parameter","severity":"ERROR","type":"COMPILE_TIME_ERROR","location":{"file":"lib/main.dart","range":{"start":{"offset":151,"line":35,"column":18},"end":{"offset":155,"line":35,"column":22}}},"problemMessage":"Expected ';' after this."},
{"code":"unused_element","severity":"WARNING","type":"STATIC_WARNING","location":{"file":"lib/main.dart","range":{"start":{"offset":1088,"line":48,"column":8},"end":{"offset":1101,"line":48,"column":21}}},"problemMessage":"The declaration '_unusedMethod' isn't referenced."},
{"code":"avoid_print","severity":"INFO","type":"LINT","location":{"file":"lib/main.dart","range":{"start":{"offset":1110,"line":49,"column":5},"end":{"offset":1115,"line":49,"column":10}}},"problemMessage":"Don't invoke 'print' in production code."}
]}'''
    
    test_project_path = "/tmp/test_project"
    modifier = CodeModificationService(test_project_path)
    
    result = modifier._parse_dart_analyze_output(complex_output, "", 1)
    
    print(f"   ✅ Parsed {len(result.errors)} errors")
    print(f"   ✅ Parsed {len(result.warnings)} warnings")
    
    # Should find 1 error, 1 warning, and ignore INFO level
    errors_found = len(result.errors) == 1
    warnings_found = len(result.warnings) >= 1
    
    print(f"   {'✅ PASS' if errors_found else '❌ FAIL'}: Found 1 error")
    print(f"   {'✅ PASS' if warnings_found else '❌ FAIL'}: Found warnings")
    
    return errors_found and warnings_found

def test_empty_output():
    """Test parsing empty dart analyze output"""
    print("\n🧪 Testing empty dart analyze output...")
    
    empty_output = '{"version":1,"diagnostics":[]}'
    
    test_project_path = "/tmp/test_project"
    modifier = CodeModificationService(test_project_path)
    
    result = modifier._parse_dart_analyze_output(empty_output, "", 0)  # success code
    
    print(f"   ✅ Parsed {len(result.errors)} errors")
    print(f"   ✅ Parsed {len(result.warnings)} warnings")
    print(f"   ✅ Success: {result.success}")
    
    success = len(result.errors) == 0 and result.success
    print(f"   {'✅ PASS' if success else '❌ FAIL'}: Empty output handled correctly")
    
    return success

def test_malformed_json():
    """Test handling malformed JSON"""
    print("\n🧪 Testing malformed JSON handling...")
    
    malformed_output = '{"version":1,"diagnostics":[invalid json here'
    
    test_project_path = "/tmp/test_project"
    modifier = CodeModificationService(test_project_path)
    
    result = modifier._parse_dart_analyze_output(malformed_output, "", 1)
    
    print(f"   ✅ Parsed {len(result.errors)} errors")
    print(f"   ✅ Success: {result.success}")
    
    # Should have at least 1 error (parse error) and success should be False
    success = len(result.errors) >= 1 and not result.success
    print(f"   {'✅ PASS' if success else '❌ FAIL'}: Malformed JSON handled correctly")
    
    return success

def test_non_json_text_output():
    """Test handling non-JSON text output (fallback)"""
    print("\n🧪 Testing non-JSON text output...")
    
    text_output = '''lib/main.dart:35:18: Error: Expected ';' after this.
int _counter = 0
^
lib/main.dart:36:10: Error: Field 'undeclaredVariable' should be initialized
String undeclaredVariable;
^^^^^^^^^^^^^^^^^^'''
    
    test_project_path = "/tmp/test_project"
    modifier = CodeModificationService(test_project_path)
    
    result = modifier._parse_dart_analyze_output(text_output, "", 1)
    
    print(f"   ✅ Parsed {len(result.errors)} errors")
    print(f"   ✅ Success: {result.success}")
    
    # Should parse text errors as fallback
    success = len(result.errors) >= 1 and not result.success
    print(f"   {'✅ PASS' if success else '❌ FAIL'}: Text output handled correctly")
    
    return success

def run_all_tests():
    """Run all dart analysis parsing tests"""
    print("🚀 Starting Dart Analysis Parsing Tests\n")
    
    tests = [
        test_parse_real_dart_analyze_output,
        test_parse_complex_dart_output,
        test_empty_output,
        test_malformed_json,
        test_non_json_text_output
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
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Dart analysis parsing is working correctly.")
    else:
        print("❌ Some tests failed. Issues found in dart analysis parsing.")
    
    return passed == total

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)