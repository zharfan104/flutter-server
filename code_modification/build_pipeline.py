"""
Build Pipeline Service
Orchestrates the complete AI-driven Flutter development workflow
"""

import asyncio
import time
import json
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from pathlib import Path

from .code_modifier import CodeModificationService, ModificationRequest, ModificationResult
from .dart_analysis import DartAnalysisService, AnalysisResult
from .iterative_fixer import IterativeErrorFixer, FixingResult
from .llm_executor import SimpleLLMExecutor

# Import advanced logging and monitoring
from utils.advanced_logger import logger, LogCategory, LogLevel, OperationTracker
from utils.request_tracer import tracer, TraceContext, EventContext, TraceEventType
from utils.performance_monitor import performance_monitor, TimingContext
from utils.error_analyzer import error_analyzer, analyze_error


@dataclass
class PipelineStep:
    """Represents a single step in the pipeline"""
    name: str
    status: str  # pending, running, completed, failed
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class PipelineResult:
    """Result of the complete pipeline execution"""
    success: bool
    total_time: float
    steps: List[PipelineStep]
    modification_result: Optional[ModificationResult] = None
    fixing_result: Optional[FixingResult] = None
    final_analysis: Optional[AnalysisResult] = None
    error_message: Optional[str] = None


class BuildPipelineService:
    """
    Main orchestrator for the AI-driven Flutter development pipeline
    Implements: User chat → Anthropic → Code modification → Hot reload → Dart analysis → Iterative fixing
    """
    
    def __init__(self, project_path: str, flutter_manager=None):
        self.project_path = Path(project_path)
        self.flutter_manager = flutter_manager
        
        # Initialize services
        self.code_modifier = CodeModificationService(str(self.project_path))
        self.dart_analyzer = DartAnalysisService(str(self.project_path))
        self.error_fixer = IterativeErrorFixer(str(self.project_path))
        
        # Status callback for real-time updates
        self.status_callback: Optional[Callable[[str], None]] = None
        
        # Pipeline configuration
        self.config = {
            "max_fix_attempts": 16,
            "enable_hot_reload": True,
            "run_final_analysis": True,
            "auto_fix_errors": True
        }
    
    def set_status_callback(self, callback: Callable[[str], None]):
        """Set callback for real-time status updates"""
        self.status_callback = callback
        self.error_fixer.set_status_callback(callback)
    
    def _update_status(self, message: str, context: Optional[Dict[str, Any]] = None):
        """Send status update if callback is set"""
        if self.status_callback:
            self.status_callback(message)
        
        # Enhanced logging with context
        logger.info(LogCategory.PIPELINE, message, context=context or {}, 
                   tags=["pipeline", "status"])
        print(f"[BuildPipeline] {message}")
    
    async def execute_pipeline(self, user_request: str, context: Optional[Dict] = None) -> PipelineResult:
        """
        Execute the complete AI-driven development pipeline
        
        Args:
            user_request: The user's development request
            context: Optional context information
            
        Returns:
            PipelineResult with detailed execution information
        """
        start_time = time.time()
        steps = []
        
        # Start comprehensive tracing
        trace_id = None
        if context and "trace_id" in context:
            trace_id = context["trace_id"]
        else:
            with TraceContext("ai_pipeline", context.get("user_id") if context else None, 
                            {"user_request": user_request[:100]}) as tid:
                trace_id = tid
        
        with OperationTracker("complete_ai_pipeline", LogCategory.PIPELINE):
            self._update_status(f"🚀 Starting AI development pipeline for: {user_request}", 
                              context={
                                  "trace_id": trace_id,
                                  "user_request": user_request[:200],
                                  "request_length": len(user_request),
                                  "context_provided": context is not None
                              })
            
            # Start performance monitoring for this pipeline
            pipeline_timer = performance_monitor.start_timer("pipeline_execution")
            
            try:
                # Step 1: Code Modification
                with EventContext(trace_id, TraceEventType.PIPELINE_STEP, "pipeline", "code_modification"):
                    step = PipelineStep(name="Code Modification", status="running", start_time=time.time())
                    steps.append(step)
                    
                    self._update_status("📝 Generating code modifications...", 
                                      context={"step": "code_modification", "trace_id": trace_id})
                    
                    modification_result = await self._execute_code_modification(user_request, context, trace_id)
                    
                    step.end_time = time.time()
                    step.result = modification_result
                    
                    if not modification_result.success:
                        step.status = "failed"
                        step.error = "; ".join(modification_result.errors)
                        
                        # Log detailed failure information
                        logger.error(LogCategory.PIPELINE, "Code modification step failed",
                                   context={
                                       "trace_id": trace_id,
                                       "errors": modification_result.errors,
                                       "warnings": modification_result.warnings,
                                       "request": user_request[:200],
                                       "step_duration": step.end_time - step.start_time
                                   })
                        
                        # Analyze the error
                        if modification_result.errors:
                            for error_msg in modification_result.errors:
                                error_analyzer.analyze_error(
                                    component="pipeline",
                                    operation="code_modification",
                                    message=error_msg,
                                    context={"trace_id": trace_id, "user_request": user_request}
                                )
                        
                        return PipelineResult(
                            success=False,
                            total_time=time.time() - start_time,
                            steps=steps,
                            modification_result=modification_result,
                            error_message=f"Code modification failed: {step.error}"
                        )
                    
                    step.status = "completed"
                    
                    # Log successful modification details
                    modification_context = {
                        "trace_id": trace_id,
                        "modified_files": modification_result.modified_files,
                        "created_files": modification_result.created_files,
                        "deleted_files": modification_result.deleted_files,
                        "changes_summary": modification_result.changes_summary,
                        "step_duration": step.end_time - step.start_time
                    }
                    
                    logger.info(LogCategory.PIPELINE, "Code modification step completed successfully",
                               context=modification_context)
                    
                    self._update_status(f"✅ Code modifications completed: {modification_result.changes_summary}",
                                      context=modification_context)
                
                # Step 2: Hot Reload (if enabled and Flutter manager available)
                if self.config["enable_hot_reload"] and self.flutter_manager:
                    step = PipelineStep(name="Hot Reload", status="running", start_time=time.time())
                    steps.append(step)
                    
                    self._update_status("🔄 Triggering hot reload...")
                    hot_reload_success = await self._execute_hot_reload()
                    
                    step.end_time = time.time()
                    step.result = {"success": hot_reload_success}
                    step.status = "completed" if hot_reload_success else "failed"
                    
                    if hot_reload_success:
                        self._update_status("✅ Hot reload completed")
                    else:
                        self._update_status("⚠️ Hot reload failed, continuing with analysis...")
                
                # Step 3: Dart Analysis
                step = PipelineStep(name="Dart Analysis", status="running", start_time=time.time())
                steps.append(step)
                
                self._update_status("🔍 Running Dart analysis...")
                analysis_result = await self._execute_dart_analysis()
                
                step.end_time = time.time()
                step.result = analysis_result
                step.status = "completed"
                
                if analysis_result.success:
                    self._update_status("✅ No errors found in analysis!")
                    return PipelineResult(
                        success=True,
                        total_time=time.time() - start_time,
                        steps=steps,
                        modification_result=modification_result,
                        final_analysis=analysis_result
                    )
                else:
                    error_count = len(analysis_result.errors)
                    self._update_status(f"⚠️ Found {error_count} errors in analysis")
                
                # Step 4: Iterative Error Fixing (if enabled and errors found)
                if self.config["auto_fix_errors"] and analysis_result.errors:
                    step = PipelineStep(name="Iterative Error Fixing", status="running", start_time=time.time())
                    steps.append(step)
                    
                    self._update_status("🔧 Starting iterative error fixing...")
                    fixing_result = await self._execute_error_fixing()
                    
                    step.end_time = time.time()
                    step.result = fixing_result
                    step.status = "completed" if fixing_result.success else "failed"
                    
                    if fixing_result.success:
                        self._update_status("✅ All errors fixed successfully!")
                    else:
                        self._update_status(f"❌ {fixing_result.final_errors} errors remain after fixing attempts")
                    
                    # Step 5: Final Hot Reload after fixing
                    if fixing_result.success and self.config["enable_hot_reload"] and self.flutter_manager:
                        step = PipelineStep(name="Final Hot Reload", status="running", start_time=time.time())
                        steps.append(step)
                        
                        self._update_status("🔄 Final hot reload after fixes...")
                        final_reload_success = await self._execute_hot_reload()
                        
                        step.end_time = time.time()
                        step.result = {"success": final_reload_success}
                        step.status = "completed" if final_reload_success else "failed"
                    
                    # Step 6: Final Analysis
                    if self.config["run_final_analysis"]:
                        step = PipelineStep(name="Final Analysis", status="running", start_time=time.time())
                        steps.append(step)
                        
                        self._update_status("🔍 Running final analysis...")
                        final_analysis = await self._execute_dart_analysis()
                        
                        step.end_time = time.time()
                        step.result = final_analysis
                        step.status = "completed"
                        
                        pipeline_success = final_analysis.success
                        if pipeline_success:
                            self._update_status("🎉 Pipeline completed successfully - no errors!")
                        else:
                            self._update_status(f"⚠️ Pipeline completed with {len(final_analysis.errors)} remaining errors")
                    else:
                        pipeline_success = fixing_result.success
                        final_analysis = fixing_result.final_analysis
                else:
                    # No auto-fixing, pipeline success depends on initial analysis
                    pipeline_success = analysis_result.success
                    fixing_result = None
                    final_analysis = analysis_result
                
                total_time = time.time() - start_time
                
                return PipelineResult(
                    success=pipeline_success,
                    total_time=total_time,
                    steps=steps,
                    modification_result=modification_result,
                    fixing_result=fixing_result,
                    final_analysis=final_analysis
                )
                
            except Exception as e:
                error_message = f"Pipeline failed with error: {str(e)}"
                self._update_status(f"❌ {error_message}")
                
                return PipelineResult(
                    success=False,
                    total_time=time.time() - start_time,
                    steps=steps,
                    error_message=error_message
                )
    
    async def _execute_code_modification(self, user_request: str, context: Optional[Dict] = None, trace_id: Optional[str] = None) -> ModificationResult:
        """Execute code modification step"""
        with TimingContext("code_modification_step"):
            logger.debug(LogCategory.CODE_MOD, "Starting code modification execution",
                        context={
                            "trace_id": trace_id,
                            "request": user_request[:200],
                            "context_keys": list(context.keys()) if context else []
                        })
            
            modification_request = ModificationRequest(
                description=user_request,
                context=context,
                request_id=trace_id or f"pipeline_{int(time.time())}"
            )
            
            result = await self.code_modifier.modify_code(modification_request)
            
            # Log the result details
            logger.debug(LogCategory.CODE_MOD, "Code modification execution completed",
                        context={
                            "trace_id": trace_id,
                            "success": result.success,
                            "modified_files_count": len(result.modified_files),
                            "created_files_count": len(result.created_files),
                            "deleted_files_count": len(result.deleted_files),
                            "errors_count": len(result.errors),
                            "warnings_count": len(result.warnings)
                        })
            
            return result
    
    async def _execute_hot_reload(self) -> bool:
        """Execute hot reload step"""
        if not self.flutter_manager:
            return False
        
        try:
            # Trigger hot reload via Flutter manager
            result = self.flutter_manager.trigger_hot_reload()
            return result.get("success", False)
        except Exception as e:
            self._update_status(f"Hot reload error: {str(e)}")
            return False
    
    async def _execute_dart_analysis(self) -> AnalysisResult:
        """Execute Dart analysis step"""
        return self.dart_analyzer.run_analysis()
    
    async def _execute_error_fixing(self) -> FixingResult:
        """Execute iterative error fixing step"""
        return await self.error_fixer.fix_all_errors(
            max_attempts=self.config["max_fix_attempts"]
        )
    
    def get_pipeline_summary(self, result: PipelineResult) -> Dict:
        """Generate a summary of the pipeline execution"""
        summary = {
            "success": result.success,
            "total_time": f"{result.total_time:.1f}s",
            "steps_completed": len([s for s in result.steps if s.status == "completed"]),
            "steps_failed": len([s for s in result.steps if s.status == "failed"]),
            "total_steps": len(result.steps),
            "steps": []
        }
        
        for step in result.steps:
            step_summary = {
                "name": step.name,
                "status": step.status,
                "time": f"{(step.end_time - step.start_time):.1f}s" if step.end_time and step.start_time else "N/A"
            }
            
            if step.error:
                step_summary["error"] = step.error
            
            summary["steps"].append(step_summary)
        
        # Add specific results
        if result.modification_result:
            summary["files_modified"] = len(result.modification_result.modified_files)
            summary["files_created"] = len(result.modification_result.created_files)
            summary["files_deleted"] = len(result.modification_result.deleted_files)
        
        if result.fixing_result:
            summary["errors_fixed"] = result.fixing_result.initial_errors - result.fixing_result.final_errors
            summary["fix_attempts"] = result.fixing_result.total_attempts
        
        if result.final_analysis:
            summary["final_errors"] = len(result.final_analysis.errors)
            summary["final_warnings"] = len(result.final_analysis.warnings)
        
        return summary
    
    def update_config(self, new_config: Dict):
        """Update pipeline configuration"""
        self.config.update(new_config)
        self._update_status(f"Pipeline configuration updated: {new_config}")
    
    async def preview_modifications(self, user_request: str, context: Optional[Dict] = None) -> Dict:
        """Preview what modifications would be made without executing the pipeline"""
        modification_request = ModificationRequest(
            description=user_request,
            context=context
        )
        
        # This would use the code modifier's preview functionality
        return self.code_modifier.preview_modifications(modification_request)
    
    def get_status(self) -> Dict:
        """Get current pipeline status"""
        return {
            "project_path": str(self.project_path),
            "flutter_manager_available": self.flutter_manager is not None,
            "config": self.config,
            "services": {
                "code_modifier": "available",
                "dart_analyzer": "available", 
                "error_fixer": "available"
            }
        }