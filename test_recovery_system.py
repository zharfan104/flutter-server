#!/usr/bin/env python3
"""
Test script for the enhanced error recovery system
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from code_modification.dart_analysis_fixer import DartAnalysisFixer, FixingConfig, fix_dart_errors
from code_modification.hot_reload_recovery import HotReloadRecoveryService


async def test_dart_analysis_fixer():
    """Test the DartAnalysisFixer directly"""
    print("🧪 Testing DartAnalysisFixer...")
    
    project_path = "./project"  # Adjust to your Flutter project path
    
    if not os.path.exists(project_path):
        print(f"❌ Project path not found: {project_path}")
        return False
    
    try:
        # Create configuration
        config = FixingConfig(
            max_attempts=3,
            enable_commands=True,
            enable_dart_fix=True,
            enable_build_runner=True,
            log_file_path="logs/test_recovery.json"
        )
        
        print(f"📁 Project: {project_path}")
        print(f"⚙️  Config: {config.max_attempts} attempts, commands enabled")
        
        # Run the fixer
        result = await fix_dart_errors(project_path, config)
        
        print(f"\n📊 Results:")
        print(f"✅ Success: {result.success}")
        print(f"🔄 Attempts: {result.attempts_made}")
        print(f"🐛 Initial Errors: {result.initial_error_count}")
        print(f"🐛 Final Errors: {result.final_error_count}")
        print(f"⚡ Commands: {len(result.commands_executed)}")
        print(f"🔧 Fixes Applied: {result.fixes_applied}")
        print(f"📝 Files Modified: {len(result.files_modified)}")
        print(f"⏱️  Duration: {result.total_duration:.1f}s")
        
        if result.commands_executed:
            print(f"\n💻 Commands Executed:")
            for cmd in result.commands_executed:
                print(f"  • {cmd}")
        
        if result.files_modified:
            print(f"\n📝 Files Modified:")
            for file in result.files_modified:
                print(f"  • {file}")
        
        if result.error_message:
            print(f"\n❌ Error: {result.error_message}")
        
        return result.success
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def test_hot_reload_recovery():
    """Test the enhanced HotReloadRecoveryService"""
    print("\n🧪 Testing Enhanced HotReloadRecoveryService...")
    
    project_path = "./project"  # Adjust to your Flutter project path
    
    if not os.path.exists(project_path):
        print(f"❌ Project path not found: {project_path}")
        return False
    
    try:
        # Initialize the service
        recovery_service = HotReloadRecoveryService(project_path)
        
        # Show status
        status = recovery_service.get_recovery_status()
        print(f"📊 Recovery Status:")
        print(f"  • Robust Recovery: {status['robust_recovery_enabled']}")
        print(f"  • Max Retries: {status['max_retries']}")
        print(f"  • Timeout: {status['recovery_timeout']}s")
        
        # Test with mock error output (since we can't easily generate real errors)
        mock_error_output = "Flutter compilation errors detected..."
        
        print(f"\n🔄 Running recovery test...")
        result = await recovery_service.attempt_recovery(
            error_output=mock_error_output,
            conversation_id="test_recovery",
            max_retries=2
        )
        
        print(f"\n📊 Recovery Results:")
        print(f"✅ Success: {result.success}")
        print(f"🔄 Attempts: {result.attempts}")
        print(f"🔧 Fix Applied: {result.fix_applied}")
        
        if result.recovery_messages:
            print(f"\n💬 Recovery Messages:")
            for msg in result.recovery_messages:
                print(f"  • {msg}")
        
        if result.final_error:
            print(f"\n❌ Final Error: {result.final_error}")
        
        return result.success
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def test_command_executor():
    """Test the CommandExecutor"""
    print("\n🧪 Testing CommandExecutor...")
    
    try:
        from code_modification.command_executor import CommandExecutor, CommandType
        
        project_path = "./project"
        if not os.path.exists(project_path):
            print(f"❌ Project path not found: {project_path}")
            return False
        
        executor = CommandExecutor(project_path)
        
        # Test flutter doctor
        print("🔍 Running flutter doctor...")
        result = await executor.execute_flutter_doctor()
        
        print(f"📊 Command Result:")
        print(f"✅ Success: {result.success}")
        print(f"💻 Command: {result.command}")
        print(f"🔢 Exit Code: {result.exit_code}")
        print(f"⏱️  Duration: {result.execution_time:.1f}s")
        
        if result.stdout:
            print(f"📤 Output: {result.stdout[:200]}...")
        
        if result.stderr:
            print(f"❌ Error: {result.stderr[:200]}...")
        
        return result.success
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("🚀 Starting Enhanced Error Recovery System Tests\n")
    
    tests = [
        ("Command Executor", test_command_executor),
        ("Dart Analysis Fixer", test_dart_analysis_fixer),
        ("Hot Reload Recovery", test_hot_reload_recovery)
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
        print("🎉 All tests passed! The enhanced error recovery system is ready.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    return passed == total


if __name__ == "__main__":
    asyncio.run(main())