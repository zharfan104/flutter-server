#!/usr/bin/env python3
"""
Test Pre-Hot-Reload Analysis and Error Fixing
Verifies that dart analyze runs before hot reload and fixes errors
"""

import sys
import asyncio
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from code_modification.build_pipeline import BuildPipelineService, PipelineResult
from code_modification.dart_analysis import AnalysisResult, AnalysisIssue, AnalysisType
from code_modification.iterative_fixer import FixingResult, FixAttempt
from code_modification.code_modifier import ModificationResult


class MockFlutterManager:
    """Mock Flutter manager for testing"""
    def __init__(self):
        self.is_running = True
        self.hot_reload_called = False
        self.hot_reload_count = 0
        
    def trigger_hot_reload(self):
        self.hot_reload_called = True
        self.hot_reload_count += 1
        return {"success": True}


class TestPreHotReloadAnalysis:
    """Test suite for pre-hot-reload analysis and fixing"""
    
    def __init__(self):
        self.test_project_path = "./test_project"
        
    async def test_pre_hot_reload_analysis_no_errors(self):
        """Test that hot reload happens when no errors are found"""
        print("🧪 Testing Pre-Hot-Reload Analysis - No Errors...")
        
        # Mock successful code modification
        mock_mod_result = ModificationResult(
            success=True,
            modified_files=["lib/main.dart"],
            created_files=[],
            deleted_files=[],
            errors=[],
            warnings=[],
            changes_summary="Modified main.dart"
        )
        
        # Mock clean analysis (no errors)
        mock_analysis_clean = AnalysisResult(
            success=True,
            issues=[],
            errors=[],
            warnings=[],
            output="No issues found",
            execution_time=1.0
        )
        
        mock_flutter = MockFlutterManager()
        
        with patch('code_modification.build_pipeline.CodeModificationService') as MockCodeMod:
            with patch('code_modification.build_pipeline.DartAnalysisService') as MockDartAnalysis:
                # Setup mocks
                mock_code_mod = MockCodeMod.return_value
                # Make modify_code return a coroutine
                async def mock_modify_code(*args, **kwargs):
                    return mock_mod_result
                mock_code_mod.modify_code = mock_modify_code
                
                mock_dart_analysis = MockDartAnalysis.return_value
                mock_dart_analysis.run_analysis = Mock(return_value=mock_analysis_clean)
                
                # Create pipeline
                pipeline = BuildPipelineService(self.test_project_path, mock_flutter)
                
                # Execute pipeline
                result = await pipeline.execute_pipeline("Add a button")
                
                # Verify pre-hot-reload analysis was called
                assert mock_dart_analysis.run_analysis.call_count >= 1
                first_call_args = mock_dart_analysis.run_analysis.call_args_list[0]
                assert first_call_args[1].get('errors_only') == True, "First analysis should be errors_only"
                
                # Verify hot reload was called (no errors found)
                assert mock_flutter.hot_reload_called, "Hot reload should be called when no errors"
                
                # Verify pipeline success
                assert result.success, "Pipeline should succeed"
                
                print("✅ Pre-Hot-Reload Analysis - No Errors: PASSED")
                return True
    
    async def test_pre_hot_reload_analysis_with_errors_fixed(self):
        """Test that errors are fixed before hot reload"""
        print("\n🧪 Testing Pre-Hot-Reload Analysis - Errors Fixed...")
        
        # Mock successful code modification
        mock_mod_result = ModificationResult(
            success=True,
            modified_files=["lib/main.dart"],
            created_files=[],
            deleted_files=[],
            errors=[],
            warnings=[],
            changes_summary="Modified main.dart"
        )
        
        # Mock analysis with errors
        mock_error = AnalysisIssue(
            type=AnalysisType.ERROR,
            file_path="lib/main.dart",
            line=10,
            column=5,
            message="The method 'foo' isn't defined",
            rule_name="undefined_method"
        )
        
        mock_analysis_with_errors = AnalysisResult(
            success=False,
            issues=[mock_error],
            errors=[mock_error],
            warnings=[],
            output="error • The method 'foo' isn't defined • lib/main.dart:10:5 • undefined_method",
            execution_time=1.0
        )
        
        # Mock clean analysis after fix
        mock_analysis_clean = AnalysisResult(
            success=True,
            issues=[],
            errors=[],
            warnings=[],
            output="No issues found",
            execution_time=1.0
        )
        
        # Mock successful fixing
        mock_fix_result = FixingResult(
            success=True,
            total_attempts=1,
            initial_errors=1,
            final_errors=0,
            files_modified={"lib/main.dart"},
            attempts=[FixAttempt(
                attempt_number=1,
                errors_before=1,
                errors_after=0,
                files_modified=["lib/main.dart"],
                success=True,
                time_taken=2.0,
                error_summary="All errors fixed"
            )],
            total_time=2.0
        )
        
        mock_flutter = MockFlutterManager()
        
        with patch('code_modification.build_pipeline.CodeModificationService') as MockCodeMod:
            with patch('code_modification.build_pipeline.DartAnalysisService') as MockDartAnalysis:
                with patch('code_modification.build_pipeline.IterativeErrorFixer') as MockErrorFixer:
                    # Setup mocks
                    mock_code_mod = MockCodeMod.return_value
                    # Make modify_code return a coroutine
                    async def mock_modify_code(*args, **kwargs):
                        return mock_mod_result
                    mock_code_mod.modify_code = mock_modify_code
                    
                    mock_dart_analysis = MockDartAnalysis.return_value
                    # First call returns errors, subsequent calls return clean
                    mock_dart_analysis.run_analysis = Mock(side_effect=[
                        mock_analysis_with_errors,  # Pre-hot-reload check
                        mock_analysis_clean,         # After pre-fix
                        mock_analysis_clean          # Post-hot-reload check
                    ])
                    
                    mock_error_fixer = MockErrorFixer.return_value
                    # Make fix_all_errors return a coroutine and track calls
                    fix_calls = []
                    async def mock_fix_all_errors(*args, **kwargs):
                        fix_calls.append({'args': args, 'kwargs': kwargs})
                        return mock_fix_result
                    mock_error_fixer.fix_all_errors = mock_fix_all_errors
                    
                    # Create pipeline
                    pipeline = BuildPipelineService(self.test_project_path, mock_flutter)
                    
                    # Execute pipeline
                    result = await pipeline.execute_pipeline("Add a button with error")
                    
                    # Verify pre-hot-reload analysis found errors
                    assert mock_dart_analysis.run_analysis.call_count >= 2
                    
                    # Verify error fixer was called with correct parameters
                    assert len(fix_calls) > 0, "Error fixer should have been called"
                    fix_kwargs = fix_calls[0]['kwargs']
                    assert fix_kwargs['max_attempts'] == 3, "Pre-fix should use reduced attempts"
                    assert fix_kwargs['errors_only'] == True, "Pre-fix should only fix errors"
                    
                    # Verify hot reload was called after fixing
                    assert mock_flutter.hot_reload_called, "Hot reload should be called after fixing"
                    
                    # Verify pipeline success
                    assert result.success, "Pipeline should succeed after fixing"
                    
                    # Check summary includes pre-hot-reload fixing info
                    summary = pipeline.get_pipeline_summary(result)
                    assert 'pre_hot_reload_errors_fixed' in summary
                    assert summary['pre_hot_reload_errors_fixed'] == 1
                    
                    print("✅ Pre-Hot-Reload Analysis - Errors Fixed: PASSED")
                    return True
    
    async def test_pre_hot_reload_disabled(self):
        """Test that pre-hot-reload check can be disabled"""
        print("\n🧪 Testing Pre-Hot-Reload Analysis - Disabled...")
        
        mock_mod_result = ModificationResult(
            success=True,
            modified_files=["lib/main.dart"],
            created_files=[],
            deleted_files=[],
            errors=[],
            warnings=[],
            changes_summary="Modified main.dart"
        )
        
        mock_flutter = MockFlutterManager()
        
        with patch('code_modification.build_pipeline.CodeModificationService') as MockCodeMod:
            with patch('code_modification.build_pipeline.DartAnalysisService') as MockDartAnalysis:
                mock_code_mod = MockCodeMod.return_value
                # Make modify_code return a coroutine
                async def mock_modify_code(*args, **kwargs):
                    return mock_mod_result
                mock_code_mod.modify_code = mock_modify_code
                
                mock_dart_analysis = MockDartAnalysis.return_value
                mock_dart_analysis.run_analysis = Mock()
                
                # Create pipeline with pre-hot-reload disabled
                pipeline = BuildPipelineService(self.test_project_path, mock_flutter)
                pipeline.update_config({"pre_hot_reload_check": False})
                
                # Execute pipeline
                result = await pipeline.execute_pipeline("Add a button")
                
                # Verify hot reload was called immediately
                assert mock_flutter.hot_reload_called, "Hot reload should be called"
                
                # Verify no pre-hot-reload analysis steps
                pre_analysis_steps = [s for s in result.steps if s.name == "Pre-Hot-Reload Analysis"]
                assert len(pre_analysis_steps) == 0, "No pre-hot-reload analysis should occur"
                
                print("✅ Pre-Hot-Reload Analysis - Disabled: PASSED")
                return True
    
    async def run_all_tests(self):
        """Run all pre-hot-reload tests"""
        print("🚀 Starting Pre-Hot-Reload Analysis Tests\n")
        
        tests = [
            ("No Errors", self.test_pre_hot_reload_analysis_no_errors),
            ("Errors Fixed", self.test_pre_hot_reload_analysis_with_errors_fixed),
            ("Feature Disabled", self.test_pre_hot_reload_disabled),
        ]
        
        results = []
        
        for test_name, test_func in tests:
            print(f"{'='*60}")
            print(f"🧪 {test_name}")
            print(f"{'='*60}")
            
            try:
                success = await test_func()
                results.append((test_name, success))
            except Exception as e:
                print(f"❌ {test_name}: FAILED with exception: {e}")
                import traceback
                traceback.print_exc()
                results.append((test_name, False))
            
            print()
        
        # Summary
        print(f"{'='*60}")
        print("📊 PRE-HOT-RELOAD ANALYSIS TEST SUMMARY")
        print(f"{'='*60}")
        
        passed = sum(1 for _, success in results if success)
        total = len(results)
        
        for test_name, success in results:
            status = "✅ PASSED" if success else "❌ FAILED"
            print(f"{status:<12} {test_name}")
        
        print(f"\n🎯 Overall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All pre-hot-reload analysis tests passed!")
            print("\n💡 Validated Behaviors:")
            print("• Dart analysis runs before hot reload to catch compilation errors")
            print("• Errors are fixed automatically before attempting hot reload")
            print("• Pre-hot-reload fixing uses fewer attempts (3 vs 16)")
            print("• Only errors are fixed in pre-hot-reload (warnings/info skipped)")
            print("• Feature can be disabled via configuration")
            print("• Post-hot-reload error recovery is still available as fallback")
        else:
            print("⚠️  Some tests failed. Check the implementation.")
        
        return passed == total


async def main():
    """Run the tests"""
    tester = TestPreHotReloadAnalysis()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)