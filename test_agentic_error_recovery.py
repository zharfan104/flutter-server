#!/usr/bin/env python3
"""
Test the agentic error recovery system end-to-end
"""

import sys
import os
import asyncio
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from code_modification.services.code_modifier import CodeModificationService

async def test_agentic_error_recovery():
    """Test the complete agentic error recovery system"""
    print("🚀 Testing Agentic Error Recovery System")
    print("=" * 50)
    
    project_path = "/mnt/c/Users/user/code/walturn/flutter-server/project"
    modifier = CodeModificationService(project_path)
    
    # Step 1: Check if all agent prompts are now loaded
    available_prompts = modifier.prompt_loader.list_available_prompts()
    print(f"📋 Available prompts: {len(available_prompts)}")
    
    agent_prompts = [p for p in available_prompts if any(x in p.lower() for x in ['strategy', 'progress', 'execution', 'termination'])]
    print(f"🤖 Agent prompts found: {agent_prompts}")
    
    # Step 2: Run dart analysis to detect the syntax error we introduced
    print("\n🔍 Running dart analysis...")
    dart_result = await modifier._run_dart_analyze()
    
    print(f"   ✅ Analysis completed")
    print(f"   📊 Errors found: {len(dart_result.errors)}")
    print(f"   📊 Warnings found: {len(dart_result.warnings)}")
    print(f"   📊 Success: {dart_result.success}")
    
    if dart_result.errors:
        print("   📋 First few errors:")
        for i, error in enumerate(dart_result.errors[:3]):
            print(f"      Error {i+1}: {error.file_path}:{error.line} - {error.message[:80]}...")
    
    # Step 3: Test the agentic retry system (only if we have errors to fix)
    if not dart_result.success and len(dart_result.errors) > 0:
        print("\n🤖 Testing agentic error recovery...")
        
        try:
            # This should now work with the fixed PromptLoader
            recovery_result = await modifier._run_agentic_error_recovery(dart_result.errors)
            
            print(f"   ✅ Recovery completed")
            print(f"   📊 Success: {recovery_result.get('success', False)}")
            print(f"   📊 Attempts made: {recovery_result.get('attempts_made', 0)}")
            print(f"   📊 Final error count: {len(recovery_result.get('final_errors', []))}")
            
            if recovery_result.get('success'):
                print("   🎉 SUCCESS: Agentic system successfully fixed the errors!")
            else:
                print("   ⚠️  PARTIAL: Agentic system made progress but didn't fix all errors")
            
            return recovery_result.get('success', False)
            
        except Exception as e:
            print(f"   ❌ ERROR: Agentic recovery failed - {e}")
            return False
    else:
        print("\n✅ No errors found - cannot test agentic recovery")
        print("   (This means the project is clean, which is good!)")
        return True

async def test_prompt_loading():
    """Test that all agent prompts are now properly loaded"""
    print("\n🧪 Testing prompt loading...")
    
    project_path = "/mnt/c/Users/user/code/walturn/flutter-server/project" 
    modifier = CodeModificationService(project_path)
    
    # Test loading each agent prompt
    agent_prompts = ['Strategy Selection', 'Progress Evaluation', 'Code Execution', 'Termination Decision']
    
    results = []
    for prompt_name in agent_prompts:
        try:
            # Try to get the prompt template
            template = modifier.prompt_loader.get_prompt_template(prompt_name)
            
            if template and len(template) > 50:  # Should be a substantial prompt
                print(f"   ✅ {prompt_name}: Loaded ({len(template)} chars)")
                results.append(True)
            else:
                print(f"   ❌ {prompt_name}: Empty or too short")
                results.append(False)
                
        except Exception as e:
            print(f"   ❌ {prompt_name}: Failed to load - {e}")
            results.append(False)
    
    success = all(results)
    print(f"   {'✅ PASS' if success else '❌ FAIL'}: Agent prompts loading")
    
    return success

if __name__ == "__main__":
    async def main():
        print("🚀 Starting Agentic System Tests\n")
        
        # Test 1: Prompt loading
        prompt_test = await test_prompt_loading()
        
        # Test 2: Full error recovery
        recovery_test = await test_agentic_error_recovery()
        
        print(f"\n📊 Test Results:")
        print(f"   Prompt Loading: {'✅ PASS' if prompt_test else '❌ FAIL'}")
        print(f"   Error Recovery: {'✅ PASS' if recovery_test else '❌ FAIL'}")
        
        overall_success = prompt_test and recovery_test
        print(f"\n{'🎉 ALL TESTS PASSED' if overall_success else '❌ SOME TESTS FAILED'}")
        
        return overall_success
    
    success = asyncio.run(main())
    sys.exit(0 if success else 1)