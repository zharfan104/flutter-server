#!/usr/bin/env python3
"""
Test the actual dart analysis with the current project
"""

import sys
import os
import asyncio
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from code_modification.services.code_modifier import CodeModificationService

async def test_real_project_analysis():
    """Test dart analysis on the actual project"""
    print("🧪 Testing dart analysis on actual project...")
    
    project_path = "/mnt/c/Users/user/code/walturn/flutter-server/project"
    modifier = CodeModificationService(project_path)
    
    try:
        result = await modifier._run_dart_analyze()
        
        print(f"   ✅ Analysis completed")
        print(f"   ✅ Errors found: {len(result.errors)}")
        print(f"   ✅ Warnings found: {len(result.warnings)}")
        print(f"   ✅ Success: {result.success}")
        print(f"   ✅ Error message: {result.error_message}")
        
        # Show first few errors
        for i, error in enumerate(result.errors[:3]):
            print(f"   📋 Error {i+1}: {error.file_path}:{error.line} - {error.message[:100]}...")
        
        if len(result.errors) > 3:
            print(f"   📋 ... and {len(result.errors) - 3} more errors")
        
        # Should find errors if they exist
        success = len(result.errors) > 0  # We expect errors in this test project
        print(f"   {'✅ PASS' if success else '❌ FAIL'}: Found errors as expected")
        
        return success
        
    except Exception as e:
        print(f"   ❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_real_project_analysis())
    sys.exit(0 if success else 1)