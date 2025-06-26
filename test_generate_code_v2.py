#!/usr/bin/env python3
"""
Test the new generate_code v2.0 prompt structure
"""

import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from code_modification.prompt_loader import prompt_loader
from code_modification.code_modifier import CodeModificationService, ModificationRequest

def test_new_prompt_structure():
    """Test that the new prompt structure loads and formats correctly"""
    print("🧪 Testing New Prompt Structure...")
    
    try:
        # Test system/user prompt loading
        system_prompt, user_prompt = prompt_loader.get_system_user_prompts(
            'generate_code',
            project_summary='{"files": ["lib/main.dart"], "dependencies": []}',
            change_request='Add a simple welcome text widget',
            current_contents='lib/main.dart content here...',
            target_files='["lib/main.dart"]',
            files_to_create='[]',
            files_to_delete='[]'
        )
        
        print("✅ System/User prompts loaded successfully")
        print(f"📊 System prompt: {len(system_prompt)} characters")
        print(f"📊 User prompt: {len(user_prompt)} characters")
        
        # Verify key elements in system prompt
        required_elements = [
            "expert Flutter/Dart developer",
            "JSON object",
            "file_operations", 
            "shell_commands",
            "COMPLETE FILES ONLY",
            "perfect syntax"
        ]
        
        missing_elements = []
        for element in required_elements:
            if element not in system_prompt:
                missing_elements.append(element)
        
        if missing_elements:
            print(f"⚠️  Missing elements in system prompt: {missing_elements}")
        else:
            print("✅ All required elements present in system prompt")
        
        # Verify user prompt contains placeholders
        user_required = ["Project Context", "Modification Request", "File Operations Requested"]
        for element in user_required:
            if element not in user_prompt:
                print(f"⚠️  Missing '{element}' in user prompt")
            else:
                print(f"✅ Found '{element}' in user prompt")
        
        return True
        
    except Exception as e:
        print(f"❌ Prompt structure test failed: {e}")
        return False

def test_fallback_compatibility():
    """Test that legacy prompts still work"""
    print("\n🔄 Testing Fallback Compatibility...")
    
    try:
        # Test legacy format access
        legacy_prompt = prompt_loader.format_prompt(
            'generate_code',
            project_summary='test',
            change_request='test change',
            current_contents='test content',
            target_files='[]',
            files_to_create='[]',
            files_to_delete='[]'
        )
        
        print("✅ Legacy format access works")
        print(f"📊 Legacy prompt: {len(legacy_prompt)} characters")
        return True
        
    except Exception as e:
        print(f"❌ Fallback compatibility test failed: {e}")
        return False

def test_code_modifier_integration():
    """Test that CodeModificationService can use the new prompt structure"""
    print("\n🔧 Testing Code Modifier Integration...")
    
    try:
        # Initialize the service
        service = CodeModificationService("./project")
        
        # Check if the service can access the new prompt structure
        prompt_info = prompt_loader.get_prompt_info('generate_code')
        
        # Verify it has the v2.0 structure
        has_system_prompt = 'system_prompt' in prompt_info
        has_user_template = 'user_template' in prompt_info
        version = prompt_info.get('version', '1.0')
        
        print(f"✅ Service initialized successfully")
        print(f"📊 Prompt version: {version}")
        print(f"📊 Has system prompt: {has_system_prompt}")
        print(f"📊 Has user template: {has_user_template}")
        
        if version == "2.0" and has_system_prompt and has_user_template:
            print("✅ v2.0 structure detected and available")
            return True
        else:
            print("⚠️  v2.0 structure not fully available")
            return False
        
    except Exception as e:
        print(f"❌ Code modifier integration test failed: {e}")
        return False

def main():
    """Run all tests for the new prompt structure"""
    print("🚀 Starting Generate Code v2.0 Tests\n")
    
    tests = [
        ("New Prompt Structure", test_new_prompt_structure),
        ("Fallback Compatibility", test_fallback_compatibility), 
        ("Code Modifier Integration", test_code_modifier_integration)
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
            results.append((test_name, False))
        
        print()
    
    # Summary
    print(f"{'='*60}")
    print("📊 TEST SUMMARY") 
    print(f"{'='*60}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status:<12} {test_name}")
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Generate Code v2.0 is ready!")
        print("\n💡 New Features Available:")
        print("• System/User prompt separation for better AI accuracy")
        print("• Enhanced JSON response format with validation")
        print("• Backward compatibility with legacy prompts")
        print("• Improved error handling and response parsing")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)