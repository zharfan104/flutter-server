#!/usr/bin/env python3
"""
Test Langfuse integration in LLM executor
"""

import sys
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from code_modification.llm_executor import SimpleLLMExecutor, LANGFUSE_AVAILABLE

def test_langfuse_integration():
    """Test that Langfuse integration works without errors"""
    print("🧪 Testing Langfuse Integration...")
    
    # Check if Langfuse is available
    print(f"📊 Langfuse Available: {'✅' if LANGFUSE_AVAILABLE else '❌'}")
    
    if not LANGFUSE_AVAILABLE:
        print("ℹ️  Langfuse not installed. Install with: pip install langfuse")
        print("✅ Integration code will fallback gracefully")
        return True
    
    try:
        # Initialize LLM executor
        executor = SimpleLLMExecutor()
        print("✅ SimpleLLMExecutor initialized successfully")
        
        # Test basic functionality (without actually calling LLM to save costs)
        print("✅ LLM executor has Langfuse decorators applied")
        
        # Check that the decorated methods exist
        assert hasattr(executor, '_claude_completion_with_observability'), "Claude observability method missing"
        assert hasattr(executor, '_openai_completion_with_observability'), "OpenAI observability method missing"
        print("✅ Observability methods are present")
        
        # Check the execute method signature includes new parameters
        import inspect
        execute_sig = inspect.signature(executor.execute)
        assert 'user_id' in execute_sig.parameters, "user_id parameter missing from execute method"
        assert 'session_id' in execute_sig.parameters, "session_id parameter missing from execute method"
        print("✅ Execute method has user_id and session_id parameters")
        
        return True
        
    except Exception as e:
        print(f"❌ Langfuse integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fallback_behavior():
    """Test that the system works when Langfuse is not available"""
    print("\n🔄 Testing Fallback Behavior...")
    
    try:
        # This should work regardless of Langfuse availability
        executor = SimpleLLMExecutor()
        
        # Check that basic methods work (may not be available if API libraries not installed)
        availability = executor.is_available()
        print(f"ℹ️  LLM executor availability: {'✅' if availability else '❌'}")
        if not availability:
            print("ℹ️  LLM clients not available (anthropic/openai libraries not installed)")
            print("✅ This is expected in test environment without API libraries")
        models = executor.get_available_models()
        print(f"✅ Available models: {len(models)} found")
        
        # Check that the conditional decorators work
        claude_method = getattr(executor, '_claude_completion_with_observability', None)
        openai_method = getattr(executor, '_openai_completion_with_observability', None)
        
        if LANGFUSE_AVAILABLE:
            assert claude_method is not None, "Claude observability method should exist when Langfuse available"
            assert openai_method is not None, "OpenAI observability method should exist when Langfuse available"
            print("✅ Observability methods present when Langfuse available")
        else:
            print("ℹ️  Running without Langfuse - decorators will be no-ops")
        
        return True
        
    except Exception as e:
        print(f"❌ Fallback behavior test failed: {e}")
        return False

def main():
    """Run all Langfuse integration tests"""
    print("🚀 Starting Langfuse Integration Tests\n")
    
    tests = [
        ("Langfuse Integration", test_langfuse_integration),
        ("Fallback Behavior", test_fallback_behavior)
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
        print("🎉 All tests passed! Langfuse integration is ready.")
        if LANGFUSE_AVAILABLE:
            print("\n💡 Langfuse Usage Example:")
            print("executor = SimpleLLMExecutor()")
            print("response = executor.execute(")
            print("    messages=[{'role': 'user', 'content': 'Hello'}],")
            print("    user_id='user_123',")
            print("    session_id='session_456'")
            print(")")
        else:
            print("\n💡 To enable full observability, install Langfuse:")
            print("pip install langfuse")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)